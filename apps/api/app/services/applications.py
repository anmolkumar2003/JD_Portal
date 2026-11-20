import hashlib
import logging
import uuid
from datetime import UTC, datetime
from pathlib import PurePath
from typing import Any

from fastapi import status
from redis.asyncio import Redis
from sqlalchemy import String, cast, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.deps import ensure_application_access, ensure_job_access, scope_applications_query
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
    ApplicationDetail,
    ApplicationFilters,
    ApplicationListItem,
    ApplyForm,
    ApplyResult,
    BoardCard,
    BoardColumn,
    BoardOut,
    DocumentOut,
    MatchResultOut,
    ParsedProfileOut,
    StageChangeIn,
)
from app.schemas.candidate import CandidateSummary
from app.schemas.job import NamedRef
from app.schemas.org import PipelineStageOut
from app.services.cv_validation import validate_cv
from app.services.jobs import public_job_conditions
from app.workers.tasks import send_email

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


async def apply(  # noqa: PLR0913 - one call carries the whole multipart submission
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
    return ApplyResult(reference_no=reference_no, job_title=job.title)


# --- Portal applications (CAND / PIPE) --------------------------------------------------------


def _stage_out(stage: PipelineStage) -> PipelineStageOut:
    return PipelineStageOut.model_validate(stage)


def _candidate_summary(candidate: Candidate) -> CandidateSummary:
    return CandidateSummary.model_validate(candidate)


def _latest_score_subquery() -> Any:
    """Latest overall_score per application (nullable when matching has not run)."""
    ranked = (
        select(
            MatchResult.application_id.label("application_id"),
            MatchResult.overall_score.label("overall_score"),
            func.row_number()
            .over(
                partition_by=MatchResult.application_id,
                order_by=MatchResult.computed_at.desc(),
            )
            .label("rn"),
        )
    ).subquery()
    return (
        select(ranked.c.overall_score)
        .where(ranked.c.application_id == Application.id, ranked.c.rn == 1)
        .correlate(Application)
        .scalar_subquery()
        .label("overall_score")
    )


def _apply_list_filters(stmt: Any, filters: ApplicationFilters) -> Any:
    if filters.job_id is not None:
        stmt = stmt.where(Application.job_id == filters.job_id)
    if filters.stage_id is not None:
        stmt = stmt.where(Application.stage_id == filters.stage_id)
    if filters.candidate_id is not None:
        stmt = stmt.where(Application.candidate_id == filters.candidate_id)
    if filters.source is not None:
        stmt = stmt.where(Candidate.source == filters.source)
    if filters.applied_from is not None:
        stmt = stmt.where(Application.applied_at >= filters.applied_from)
    if filters.applied_to is not None:
        stmt = stmt.where(Application.applied_at <= filters.applied_to)
    if filters.q and filters.q.strip():
        term = filters.q.strip()
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        skill_match = (
            select(ParsedProfile.id)
            .where(
                ParsedProfile.candidate_id == Candidate.id,
                cast(ParsedProfile.data, String).ilike(f"%{escaped}%", escape="\\"),
            )
            .exists()
        )
        full_name = func.concat(Candidate.first_name, " ", Candidate.last_name)
        stmt = stmt.where(
            or_(
                Candidate.first_name.icontains(term, autoescape=True),
                Candidate.last_name.icontains(term, autoescape=True),
                full_name.icontains(term, autoescape=True),
                Candidate.email.icontains(term, autoescape=True),
                skill_match,
            )
        )
    return stmt


async def list_applications(
    session: AsyncSession, user: User, params: PageParams, filters: ApplicationFilters
) -> tuple[list[ApplicationListItem], int]:
    score = _latest_score_subquery()
    stmt = scope_applications_query(
        user,
        select(Application, Candidate, PipelineStage, Job, score).join(
            Candidate, Candidate.id == Application.candidate_id
        ),
    ).join(PipelineStage, PipelineStage.id == Application.stage_id)
    stmt = stmt.where(Candidate.deleted_at.is_(None))
    stmt = _apply_list_filters(stmt, filters)

    sortable: dict[str, Any] = {
        "applied_at": Application.applied_at,
        "stage_entered_at": Application.stage_entered_at,
        "reference_no": Application.reference_no,
        "status": Application.status,
        "candidate_name": Candidate.last_name,
        "overall_score": score,
    }
    stmt = apply_sort(stmt, params.sort, sortable, default="-applied_at")
    rows, total = await paginate(session, stmt, params)
    items: list[ApplicationListItem] = []
    for application, candidate, stage, job, overall_score in rows:
        items.append(
            ApplicationListItem(
                id=application.id,
                reference_no=application.reference_no,
                status=application.status,
                applied_at=application.applied_at,
                stage_entered_at=application.stage_entered_at,
                stage=_stage_out(stage),
                job=NamedRef(id=job.id, name=job.title),
                candidate=_candidate_summary(candidate),
                overall_score=overall_score,
                source=candidate.source,
            )
        )
    return items, total


async def get_application(
    session: AsyncSession, user: User, application_id: uuid.UUID
) -> ApplicationDetail:
    await ensure_application_access(session, user, application_id)
    row = (
        await session.execute(
            select(Application, Candidate, PipelineStage, Job)
            .join(Candidate, Candidate.id == Application.candidate_id)
            .join(PipelineStage, PipelineStage.id == Application.stage_id)
            .join(Job, Job.id == Application.job_id)
            .where(Application.id == application_id, Candidate.deleted_at.is_(None))
        )
    ).one_or_none()
    if row is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Application not found")
    application, candidate, stage, job = row

    documents = (
        await session.scalars(
            select(Document)
            .where(Document.application_id == application.id)
            .order_by(Document.is_primary.desc(), Document.created_at.desc())
        )
    ).all()

    primary_doc = next((d for d in documents if d.is_primary), documents[0] if documents else None)
    parsed: ParsedProfile | None = None
    if primary_doc is not None:
        parsed = await session.scalar(
            select(ParsedProfile)
            .where(ParsedProfile.document_id == primary_doc.id)
            .order_by(ParsedProfile.created_at.desc())
            .limit(1)
        )

    match = await session.scalar(
        select(MatchResult)
        .where(MatchResult.application_id == application.id)
        .order_by(MatchResult.computed_at.desc())
        .limit(1)
    )

    return ApplicationDetail(
        id=application.id,
        reference_no=application.reference_no,
        status=application.status,
        applied_at=application.applied_at,
        stage_entered_at=application.stage_entered_at,
        rejection_reason=application.rejection_reason,
        cover_letter=application.cover_letter,
        stage=_stage_out(stage),
        job=NamedRef(id=job.id, name=job.title),
        candidate=_candidate_summary(candidate),
        documents=[DocumentOut.model_validate(d) for d in documents],
        parsed_profile=ParsedProfileOut.model_validate(parsed) if parsed else None,
        match_result=MatchResultOut.model_validate(match) if match else None,
    )


async def change_stage(
    session: AsyncSession, user: User, application_id: uuid.UUID, body: StageChangeIn
) -> ApplicationDetail:
    await ensure_application_access(session, user, application_id)
    application = await session.get(Application, application_id)
    if application is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Application not found")

    from_stage = await session.get(PipelineStage, application.stage_id)
    to_stage = await session.scalar(
        select(PipelineStage).where(
            PipelineStage.id == body.stage_id, PipelineStage.org_id == user.org_id
        )
    )
    if to_stage is None:
        raise AppError(status.HTTP_400_BAD_REQUEST, "invalid_stage", "Pipeline stage not found")

    if to_stage.type == StageType.REJECTED:
        if not body.rejection_reason or not body.rejection_reason.strip():
            raise AppError(
                status.HTTP_400_BAD_REQUEST,
                "rejection_reason_required",
                "A rejection reason is required when moving to the Rejected stage",
            )
        application.status = ApplicationStatus.REJECTED
        application.rejection_reason = body.rejection_reason.strip()
    else:
        if application.status == ApplicationStatus.REJECTED:
            application.status = ApplicationStatus.ACTIVE
            application.rejection_reason = None
        if to_stage.type == StageType.HIRED:
            application.status = ApplicationStatus.HIRED

    now = datetime.now(UTC)
    previous_stage_id = application.stage_id
    if previous_stage_id != to_stage.id:
        application.stage_id = to_stage.id
        application.stage_entered_at = now

    meta: dict[str, Any] = {
        "from_stage_id": str(previous_stage_id),
        "to_stage_id": str(to_stage.id),
        "from_stage": from_stage.name if from_stage else None,
        "to_stage": to_stage.name,
    }
    if application.rejection_reason and to_stage.type == StageType.REJECTED:
        meta["rejection_reason"] = application.rejection_reason

    session.add(
        ActivityLog(
            candidate_id=application.candidate_id,
            application_id=application.id,
            actor_id=user.id,
            action="application.stage_changed",
            meta=meta,
            occurred_at=now,
        )
    )
    await session.commit()
    return await get_application(session, user, application_id)


async def get_board(session: AsyncSession, user: User, job_id: uuid.UUID) -> BoardOut:
    await ensure_job_access(session, user, job_id)
    job = await session.get(Job, job_id)
    if job is None or job.org_id != user.org_id or job.deleted_at is not None:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Job not found")

    stages = (
        await session.scalars(
            select(PipelineStage)
            .where(PipelineStage.org_id == user.org_id)
            .order_by(PipelineStage.order)
        )
    ).all()

    score = _latest_score_subquery()
    app_rows = (
        await session.execute(
            select(Application, Candidate, score)
            .join(Candidate, Candidate.id == Application.candidate_id)
            .where(Application.job_id == job_id, Candidate.deleted_at.is_(None))
            .order_by(Application.stage_entered_at.asc())
        )
    ).all()

    by_stage: dict[uuid.UUID, list[BoardCard]] = {stage.id: [] for stage in stages}
    for application, candidate, overall_score in app_rows:
        card = BoardCard(
            id=application.id,
            candidate_id=candidate.id,
            first_name=candidate.first_name,
            last_name=candidate.last_name,
            current_title=candidate.current_title,
            stage_entered_at=application.stage_entered_at,
            overall_score=overall_score,
            reference_no=application.reference_no,
        )
        by_stage.setdefault(application.stage_id, []).append(card)

    columns = [
        BoardColumn(
            stage=_stage_out(stage),
            count=len(by_stage.get(stage.id, [])),
            cards=by_stage.get(stage.id, []),
        )
        for stage in stages
    ]
    return BoardOut(job_id=job_id, stages=columns)
