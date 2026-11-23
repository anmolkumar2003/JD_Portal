import hashlib
import logging
import uuid
from datetime import UTC, date, datetime, time
from pathlib import PurePath
from typing import Any

from fastapi import status
from redis.asyncio import Redis
from sqlalchemy import Select, cast, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import String

from app.core import storage
from app.core.deps import ensure_job_access, scope_jobs_query
from app.core.errors import AppError
from app.core.pagination import PageParams, apply_sort, paginate
from app.core.rate_limit import enforce_rate_limit
from app.models import (
    ActivityLog,
    Application,
    Candidate,
    Document,
    Job,
    MatchResult,
    ParsedProfile,
    PipelineStage,
    User,
)
from app.models.candidate import APPLICATION_REFERENCE_SEQ
from app.models.enums import ApplicationStatus, DocumentType, StageType
from app.schemas.application import (
    ApplicationFilters,
    ApplicationListItem,
    ApplicationOut,
    ApplyForm,
    ApplyResult,
    BoardCard,
    BoardColumn,
    BoardOut,
    CandidateSummary,
    DocumentOut,
    MatchResultOut,
    ParsedProfileOut,
    StagePatch,
    StageRef,
    TimelineEntry,
)
from app.schemas.job import NamedRef
from app.services.cv_validation import validate_cv
from app.services.jobs import public_job_conditions
from app.services.salary import (
    candidate_budget,
    current_salary,
    expected_salary,
    offered_salary,
)
from app.workers.tasks import process_document, send_email

logger = logging.getLogger(__name__)

CONSENT_VERSION = "2026-11"
APPLY_LIMIT_PER_HOUR = 5
APPLY_RATE_KEY = "ratelimit:apply:{ip}"

_PROFILE_FIELDS = (
    "first_name",
    "last_name",
    "phone",
    "current_location",
    "current_company",
    "current_title",
    "total_experience_years",
    "expected_ctc",
    "notice_period_days",
    "linkedin_url",
)


def _already_applied() -> AppError:
    return AppError(
        status.HTTP_409_CONFLICT,
        "already_applied",
        "You have already applied for this job with this email address.",
    )


def _safe_file_name(name: str | None, extension: str) -> str:
    base = PurePath(name or "").name.strip()[:200]
    return base or f"cv.{extension}"


async def _applied_stage(session: AsyncSession, org_id: uuid.UUID) -> PipelineStage:
    stage = await session.scalar(
        select(PipelineStage)
        .where(PipelineStage.org_id == org_id, PipelineStage.type == StageType.APPLIED)
        .order_by(PipelineStage.order)
        .limit(1)
    )
    if stage is None:
        raise AppError(
            status.HTTP_409_CONFLICT, "not_accepting", "This job is not accepting applications."
        )
    return stage


async def _upsert_candidate(
    session: AsyncSession, org_id: uuid.UUID, form: ApplyForm, now: datetime
) -> Candidate:
    """APPLY-07: one candidate per email per org; a repeat applicant's details are refreshed."""
    email = form.email.lower()
    candidate = await session.scalar(
        select(Candidate).where(
            Candidate.org_id == org_id, Candidate.email == email, Candidate.deleted_at.is_(None)
        )
    )
    if candidate is None:
        candidate = Candidate(org_id=org_id, email=email)
        session.add(candidate)
    for field in _PROFILE_FIELDS:
        value = getattr(form, field)
        if value is not None:
            setattr(candidate, field, value)
    candidate.consent_given_at = now
    candidate.consent_version = CONSENT_VERSION
    await session.flush()
    return candidate


def _confirmation_email(candidate: Candidate, job: Job, reference_no: str) -> tuple[str, str]:
    subject = f"Application received: {job.title} ({reference_no})"
    body = (
        f"Hi {candidate.first_name},\n\n"
        f"Thank you for applying for the {job.title} role. We have received your application "
        f"and CV.\n\n"
        f"Your reference number is {reference_no}. Please quote it if you contact us.\n\n"
        "Our recruiting team will review your application and get back to you.\n\n"
        "Best regards,\nThe Recruiting Team"
    )
    return subject, body


async def apply(
    session: AsyncSession,
    redis: Redis,
    *,
    slug: str,
    form: ApplyForm,
    cv_bytes: bytes,
    cv_file_name: str | None,
    client_ip: str,
) -> ApplyResult:
    await enforce_rate_limit(redis, APPLY_RATE_KEY.format(ip=client_ip), APPLY_LIMIT_PER_HOUR, 3600)
    if form.website:
        raise AppError(status.HTTP_400_BAD_REQUEST, "invalid_submission", "Invalid submission.")

    job = await session.scalar(select(Job).where(Job.slug == slug, *public_job_conditions()))
    if job is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Job not found")
    validated = validate_cv(cv_bytes)
    stage = await _applied_stage(session, job.org_id)

    now = datetime.now(UTC)
    candidate = await _upsert_candidate(session, job.org_id, form, now)
    duplicate = await session.scalar(
        select(Application.id).where(
            Application.candidate_id == candidate.id, Application.job_id == job.id
        )
    )
    if duplicate is not None:
        raise _already_applied()

    sequence = int(await session.scalar(select(APPLICATION_REFERENCE_SEQ.next_value())) or 0)
    reference_no = f"APP-{now.year}-{sequence:06d}"
    application = Application(
        candidate_id=candidate.id,
        job_id=job.id,
        stage_id=stage.id,
        reference_no=reference_no,
        cover_letter=form.cover_letter,
        applied_at=now,
        stage_entered_at=now,
    )
    session.add(application)
    await session.flush()

    await session.execute(
        update(Document)
        .where(Document.candidate_id == candidate.id, Document.type == DocumentType.CV)
        .values(is_primary=False)
    )
    document_id = uuid.uuid4()
    storage_key = f"{job.org_id}/{candidate.id}/{document_id}.{validated.extension}"
    session.add_all(
        [
            Document(
                id=document_id,
                candidate_id=candidate.id,
                application_id=application.id,
                type=DocumentType.CV,
                file_name=_safe_file_name(cv_file_name, validated.extension),
                mime_type=validated.mime_type,
                size=len(cv_bytes),
                storage_key=storage_key,
                checksum=hashlib.sha256(cv_bytes).hexdigest(),
                is_primary=True,
                virus_scan_status=validated.virus_scan_status,
            ),
            ParsedProfile(document_id=document_id, candidate_id=candidate.id),
            ActivityLog(
                candidate_id=candidate.id,
                application_id=application.id,
                action="application.created",
                meta={"job_id": str(job.id), "reference_no": reference_no, "source": "careers"},
            ),
        ]
    )
    await session.flush()

    await storage.put_object(storage_key, cv_bytes, validated.mime_type)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        await storage.delete_object(storage_key)
        raise _already_applied() from exc
    except Exception:
        await session.rollback()
        await storage.delete_object(storage_key)
        raise

    subject, body = _confirmation_email(candidate, job, reference_no)
    try:
        send_email.delay(candidate.email, subject, body)
    except Exception:  # the application is saved; a broker outage must not fail the request
        logger.exception("failed to queue confirmation email for %s", reference_no)
    try:
        process_document.delay(str(document_id))
    except Exception:
        logger.exception("failed to queue process_document for document_id=%s", document_id)
    return ApplyResult(reference_no=reference_no, job_title=job.title)


# --- Portal reads / stage moves (CAND-01..04, CAND-09, PIPE-01/02) -----------------------------


def _app_not_found() -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "not_found", "Application not found")


def _candidate_not_found() -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "not_found", "Candidate not found")


def _stage_ref(stage: PipelineStage) -> StageRef:
    return StageRef(id=stage.id, name=stage.name, type=stage.type, order=stage.order)


def _score_subquery() -> Any:
    return (
        select(MatchResult.overall_score)
        .where(MatchResult.application_id == Application.id)
        .order_by(MatchResult.computed_at.desc())
        .limit(1)
        .correlate(Application)
        .scalar_subquery()
        .label("overall_score")
    )


def _scope_app_query(user: User, stmt: Select[Any]) -> Select[Any]:
    return scope_jobs_query(user, stmt)


def _day_bounds(day: date, *, end: bool) -> datetime:
    boundary = time.max if end else time.min
    return datetime.combine(day, boundary, tzinfo=UTC)


def _list_item(
    application: Application,
    candidate: Candidate,
    job: Job,
    stage: PipelineStage,
    score: int | None,
) -> ApplicationListItem:
    return ApplicationListItem(
        id=application.id,
        reference_no=application.reference_no,
        status=application.status,
        candidate_id=candidate.id,
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        email=candidate.email,
        current_title=candidate.current_title,
        current_company=candidate.current_company,
        source=candidate.source,
        job=NamedRef(id=job.id, name=job.title),
        stage=_stage_ref(stage),
        overall_score=score,
        is_shortlisted=application.is_shortlisted,
        tags=list(candidate.tags or []),
        expected_ctc=candidate.expected_ctc,
        budget_status=candidate_budget(candidate, job.salary_max, job.salary_min),
        applied_at=application.applied_at,
        stage_entered_at=application.stage_entered_at,
    )


async def list_applications(
    session: AsyncSession, user: User, params: PageParams, filters: ApplicationFilters
) -> tuple[list[ApplicationListItem], int]:
    score = _score_subquery()
    stmt = _scope_app_query(
        user,
        select(Application, Candidate, Job, PipelineStage, score)
        .join(Job, Job.id == Application.job_id)
        .join(Candidate, Candidate.id == Application.candidate_id)
        .join(PipelineStage, PipelineStage.id == Application.stage_id)
        .where(Candidate.deleted_at.is_(None)),
    )
    if filters.job_id is not None:
        stmt = stmt.where(Application.job_id == filters.job_id)
    if filters.stage_id is not None:
        stmt = stmt.where(Application.stage_id == filters.stage_id)
    if filters.candidate_id is not None:
        stmt = stmt.where(Application.candidate_id == filters.candidate_id)
    if filters.department_id is not None:
        stmt = stmt.where(
            func.coalesce(Candidate.department_id, Job.department_id) == filters.department_id
        )
    if filters.source is not None:
        stmt = stmt.where(Candidate.source == filters.source)
    if filters.applied_from is not None:
        stmt = stmt.where(Application.applied_at >= _day_bounds(filters.applied_from, end=False))
    if filters.applied_to is not None:
        stmt = stmt.where(Application.applied_at <= _day_bounds(filters.applied_to, end=True))
    if filters.score_min is not None:
        stmt = stmt.where(score.is_not(None), score >= filters.score_min)
    if filters.score_max is not None:
        stmt = stmt.where(score.is_not(None), score <= filters.score_max)
    if filters.skill and filters.skill.strip():
        skill_q = filters.skill.strip()
        skill_filter = (
            select(ParsedProfile.id)
            .where(
                ParsedProfile.candidate_id == Candidate.id,
                cast(ParsedProfile.data, String).icontains(skill_q, autoescape=True),
            )
            .correlate(Candidate)
            .exists()
        )
        stmt = stmt.where(skill_filter)
    if filters.tag and filters.tag.strip():
        tag = filters.tag.strip()
        stmt = stmt.where(Candidate.tags.contains([tag]))
    if filters.is_shortlisted is not None:
        stmt = stmt.where(Application.is_shortlisted.is_(filters.is_shortlisted))
    if filters.q and filters.q.strip():
        q = filters.q.strip()
        # Trigram similarity (pg_trgm indexes on first/last name) plus email / skill ILIKE.
        skill_match = (
            select(ParsedProfile.id)
            .where(
                ParsedProfile.candidate_id == Candidate.id,
                cast(ParsedProfile.data, String).icontains(q, autoescape=True),
            )
            .correlate(Candidate)
            .exists()
        )
        similarity = func.greatest(
            func.similarity(Candidate.first_name, q),
            func.similarity(Candidate.last_name, q),
            func.similarity(func.concat(Candidate.first_name, " ", Candidate.last_name), q),
        )
        stmt = stmt.where(
            or_(
                similarity > 0.25,
                Candidate.first_name.icontains(q, autoescape=True),
                Candidate.last_name.icontains(q, autoescape=True),
                Candidate.email.icontains(q, autoescape=True),
                Candidate.phone.icontains(q, autoescape=True),
                skill_match,
            )
        )

    sortable: dict[str, Any] = {
        "applied_at": Application.applied_at,
        "stage_entered_at": Application.stage_entered_at,
        "first_name": Candidate.first_name,
        "last_name": Candidate.last_name,
        "email": Candidate.email,
        "overall_score": score,
        "reference_no": Application.reference_no,
    }
    stmt = apply_sort(stmt, params.sort, sortable, default="-applied_at")
    rows, total = await paginate(session, stmt, params)
    return [_list_item(*row) for row in rows], total


async def _get_scoped_application(
    session: AsyncSession, user: User, application_id: uuid.UUID
) -> tuple[Application, Candidate, Job, PipelineStage]:
    row = (
        await session.execute(
            _scope_app_query(
                user,
                select(Application, Candidate, Job, PipelineStage)
                .join(Job, Job.id == Application.job_id)
                .join(Candidate, Candidate.id == Application.candidate_id)
                .join(PipelineStage, PipelineStage.id == Application.stage_id)
                .where(Application.id == application_id, Candidate.deleted_at.is_(None)),
            )
        )
    ).one_or_none()
    if row is None:
        raise _app_not_found()
    return row[0], row[1], row[2], row[3]


async def get_application(
    session: AsyncSession, user: User, application_id: uuid.UUID
) -> ApplicationOut:
    application, candidate, job, stage = await _get_scoped_application(
        session, user, application_id
    )
    documents = list(
        await session.scalars(
            select(Document)
            .where(Document.application_id == application.id)
            .order_by(Document.is_primary.desc(), Document.created_at.desc())
        )
    )
    # Fall back to the candidate's primary CV if none are linked to this application.
    if not documents:
        documents = list(
            await session.scalars(
                select(Document)
                .where(
                    Document.candidate_id == candidate.id,
                    Document.type == DocumentType.CV,
                    Document.is_primary.is_(True),
                )
                .limit(5)
            )
        )

    profile = await session.scalar(
        select(ParsedProfile)
        .where(ParsedProfile.candidate_id == candidate.id)
        .order_by(ParsedProfile.created_at.desc())
        .limit(1)
    )
    match = await session.scalar(
        select(MatchResult)
        .where(MatchResult.application_id == application.id)
        .order_by(MatchResult.computed_at.desc())
        .limit(1)
    )

    return ApplicationOut(
        id=application.id,
        reference_no=application.reference_no,
        status=application.status,
        rejection_reason=application.rejection_reason,
        cover_letter=application.cover_letter,
        applied_at=application.applied_at,
        stage_entered_at=application.stage_entered_at,
        is_shortlisted=application.is_shortlisted,
        candidate=CandidateSummary(
            id=candidate.id,
            first_name=candidate.first_name,
            last_name=candidate.last_name,
            email=candidate.email,
            phone=candidate.phone,
            current_location=candidate.current_location,
            current_company=candidate.current_company,
            current_title=candidate.current_title,
            total_experience_years=candidate.total_experience_years,
            expected_ctc=candidate.expected_ctc,
            current_salary=current_salary(candidate),
            expected_salary=expected_salary(candidate),
            offered_salary=offered_salary(candidate),
            notice_period_days=candidate.notice_period_days,
            linkedin_url=candidate.linkedin_url,
            portfolio_url=candidate.portfolio_url,
            department_id=candidate.department_id,
            source=candidate.source,
            tags=list(candidate.tags or []),
        ),
        job=NamedRef(id=job.id, name=job.title),
        stage=_stage_ref(stage),
        documents=[DocumentOut.model_validate(doc) for doc in documents],
        budget_status=candidate_budget(candidate, job.salary_max, job.salary_min),
        job_salary_min=job.salary_min,
        job_salary_max=job.salary_max,
        job_salary_currency=job.salary_currency,
        parsed_profile=(
            ParsedProfileOut(
                id=profile.id,
                document_id=profile.document_id,
                parse_status=profile.parse_status,
                data=profile.data or {},
                corrected_data=profile.corrected_data,
                total_experience_years=profile.total_experience_years,
                confidence=profile.confidence or {},
                error=profile.error,
                parser_version=profile.parser_version,
            )
            if profile is not None
            else None
        ),
        match_result=(
            MatchResultOut(
                overall_score=match.overall_score,
                breakdown=match.breakdown or {},
                matched_skills=list(match.matched_skills or []),
                missing_required=list(match.missing_required or []),
                missing_preferred=list(match.missing_preferred or []),
                extra_skills=list(match.extra_skills or []),
                explanation=match.explanation or {},
                engine_version=match.engine_version,
                computed_at=match.computed_at,
            )
            if match is not None
            else None
        ),
    )


async def get_board(session: AsyncSession, user: User, job_id: uuid.UUID) -> BoardOut:
    await ensure_job_access(session, user, job_id)
    job = await session.get(Job, job_id)
    if job is None or job.deleted_at is not None:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Job not found")

    stages = list(
        await session.scalars(
            select(PipelineStage)
            .where(PipelineStage.org_id == user.org_id)
            .order_by(PipelineStage.order)
        )
    )
    score = _score_subquery()
    rows = (
        await session.execute(
            select(Application, Candidate, score)
            .join(Candidate, Candidate.id == Application.candidate_id)
            .where(
                Application.job_id == job_id,
                Candidate.deleted_at.is_(None),
            )
            .order_by(Application.stage_entered_at.desc())
        )
    ).all()

    by_stage: dict[uuid.UUID, list[BoardCard]] = {stage.id: [] for stage in stages}
    for application, candidate, overall_score in rows:
        card = BoardCard(
            id=application.id,
            candidate_id=candidate.id,
            first_name=candidate.first_name,
            last_name=candidate.last_name,
            current_title=candidate.current_title,
            overall_score=overall_score,
            stage_entered_at=application.stage_entered_at,
            applied_at=application.applied_at,
            reference_no=application.reference_no,
            budget_status=candidate_budget(candidate, job.salary_max, job.salary_min),
        )
        by_stage.setdefault(application.stage_id, []).append(card)

    return BoardOut(
        job_id=job.id,
        job_title=job.title,
        stages=[
            BoardColumn(
                stage=_stage_ref(stage),
                count=len(by_stage.get(stage.id, [])),
                cards=by_stage.get(stage.id, []),
            )
            for stage in stages
        ],
    )


async def apply_stage_change(
    session: AsyncSession,
    user: User,
    application: Application,
    candidate: Candidate,
    current_stage: PipelineStage,
    body: StagePatch,
) -> bool:
    """Validate and apply a stage move without committing. Returns False if nothing changed."""
    new_stage = await session.scalar(
        select(PipelineStage).where(
            PipelineStage.id == body.stage_id, PipelineStage.org_id == user.org_id
        )
    )
    if new_stage is None:
        raise AppError(status.HTTP_400_BAD_REQUEST, "invalid_stage", "Unknown pipeline stage")

    if new_stage.type == StageType.REJECTED and not (body.reason and body.reason.strip()):
        raise AppError(
            status.HTTP_400_BAD_REQUEST,
            "rejection_reason_required",
            "A rejection reason is required when moving to the Rejected stage",
        )

    if application.stage_id == new_stage.id:
        return False

    now = datetime.now(UTC)
    previous_stage_id = application.stage_id
    previous_stage_name = current_stage.name
    application.stage_id = new_stage.id
    application.stage_entered_at = now

    if new_stage.type == StageType.REJECTED:
        application.status = ApplicationStatus.REJECTED
        application.rejection_reason = body.reason.strip() if body.reason else None
    elif new_stage.type == StageType.HIRED:
        application.status = ApplicationStatus.HIRED
        application.rejection_reason = None
    elif application.status == ApplicationStatus.REJECTED:
        application.status = ApplicationStatus.ACTIVE
        application.rejection_reason = None

    meta: dict[str, Any] = {
        "from_stage_id": str(previous_stage_id),
        "from_stage_name": previous_stage_name,
        "to_stage_id": str(new_stage.id),
        "to_stage_name": new_stage.name,
        "to_stage_type": new_stage.type.value,
    }
    if body.reason:
        meta["reason"] = body.reason.strip()

    session.add(
        ActivityLog(
            candidate_id=candidate.id,
            application_id=application.id,
            actor_id=user.id,
            action="application.stage_changed",
            meta=meta,
            occurred_at=now,
        )
    )
    return True


async def move_stage(
    session: AsyncSession, user: User, application_id: uuid.UUID, body: StagePatch
) -> ApplicationOut:
    application, candidate, _job, current_stage = await _get_scoped_application(
        session, user, application_id
    )
    if await apply_stage_change(session, user, application, candidate, current_stage, body):
        await session.commit()
        # PIPE-03: stage-triggered email (best-effort; never fails the stage move)
        try:
            from app.services.emails import maybe_send_stage_email

            new_stage = await session.get(PipelineStage, application.stage_id)
            if new_stage is not None:
                await maybe_send_stage_email(session, user, application, new_stage)
        except Exception:
            logger.exception("stage_email_failed application_id=%s", application_id)
    return await get_application(session, user, application_id)


async def candidate_timeline(
    session: AsyncSession, user: User, candidate_id: uuid.UUID
) -> list[TimelineEntry]:
    candidate = await session.get(Candidate, candidate_id)
    if candidate is None or candidate.deleted_at is not None or candidate.org_id != user.org_id:
        raise _candidate_not_found()

    # Candidate is visible only if the user can access at least one of their applications.
    accessible = await session.scalar(
        _scope_app_query(
            user,
            select(Application.id)
            .join(Job, Job.id == Application.job_id)
            .where(Application.candidate_id == candidate_id)
            .limit(1),
        )
    )
    if accessible is None:
        raise _candidate_not_found()

    rows = (
        await session.execute(
            select(ActivityLog, User.full_name)
            .outerjoin(User, User.id == ActivityLog.actor_id)
            .where(ActivityLog.candidate_id == candidate_id)
            .order_by(ActivityLog.occurred_at.desc())
            .limit(200)
        )
    ).all()
    return [
        TimelineEntry(
            id=log.id,
            action=log.action,
            occurred_at=log.occurred_at,
            actor_name=actor_name,
            application_id=log.application_id,
            meta=log.meta or {},
        )
        for log, actor_name in rows
    ]


async def list_pipeline_stages(session: AsyncSession, user: User) -> list[StageRef]:
    stages = await session.scalars(
        select(PipelineStage)
        .where(PipelineStage.org_id == user.org_id)
        .order_by(PipelineStage.order)
    )
    return [_stage_ref(stage) for stage in stages]
