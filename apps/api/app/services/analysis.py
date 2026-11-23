"""CV analysis endpoints: analysis, reprocess, corrections, rescore. CV-04..CV-10."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.db import sync_session
from app.core.deps import can_access_job
from app.core.errors import AppError
from app.models import (
    ActivityLog,
    Application,
    AtsCheck,
    Candidate,
    Document,
    Job,
    MatchResult,
    ParsedProfile,
    User,
)
from app.models.enums import ApplicationStatus, CandidateSource, DocumentType, ParseStatus
from app.schemas.application import (
    AnalysisOut,
    AtsCheckOut,
    CvParseOut,
    DuplicateCheckOut,
    ManualCandidateCreate,
    ManualCandidateResult,
    MatchResultOut,
    ParsedProfileOut,
    ParsedProfilePatch,
    ReprocessOut,
    RescoreOut,
)
from app.services.applications import _applied_stage, _safe_file_name
from app.services.cv_processing import process_document_sync, score_application
from app.services.cv_validation import validate_cv
from app.workers.tasks import process_document, rescore_job

logger = logging.getLogger(__name__)


def _not_found(entity: str = "Resource") -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "not_found", f"{entity} not found")


def _ats_band(score: int) -> str:
    if score >= 80:
        return "good"
    if score >= 60:
        return "needs_improvement"
    return "poor"


async def get_analysis(session: AsyncSession, user: User, application_id: uuid.UUID) -> AnalysisOut:
    row = (
        await session.execute(
            select(Application, Candidate, Job)
            .join(Candidate, Candidate.id == Application.candidate_id)
            .join(Job, Job.id == Application.job_id)
            .where(Application.id == application_id, Candidate.deleted_at.is_(None))
        )
    ).one_or_none()
    if row is None:
        raise _not_found("Application")
    application, candidate, job = row
    if candidate.org_id != user.org_id or not await can_access_job(session, user, job.id):
        raise _not_found("Application")

    profile = await session.scalar(
        select(ParsedProfile)
        .where(ParsedProfile.candidate_id == candidate.id)
        .order_by(ParsedProfile.created_at.desc())
        .limit(1)
    )
    document_id = profile.document_id if profile else None
    ats = None
    if document_id is not None:
        ats = await session.scalar(
            select(AtsCheck)
            .where(AtsCheck.document_id == document_id)
            .order_by(AtsCheck.created_at.desc())
            .limit(1)
        )
    match = await session.scalar(
        select(MatchResult)
        .where(MatchResult.application_id == application.id)
        .order_by(MatchResult.computed_at.desc())
        .limit(1)
    )

    return AnalysisOut(
        application_id=application.id,
        document_id=document_id,
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
            if profile
            else None
        ),
        ats_check=(
            AtsCheckOut(
                score=ats.score,
                checks=list(ats.checks or []),
                engine_version=ats.engine_version,
                band=_ats_band(ats.score),
            )
            if ats
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
            if match
            else None
        ),
    )


async def reprocess_document(
    session: AsyncSession, user: User, document_id: uuid.UUID
) -> ReprocessOut:
    row = (
        await session.execute(
            select(Document, Candidate)
            .join(Candidate, Candidate.id == Document.candidate_id)
            .where(Document.id == document_id, Candidate.deleted_at.is_(None))
        )
    ).one_or_none()
    if row is None:
        raise _not_found("Document")
    document, candidate = row
    if candidate.org_id != user.org_id:
        raise _not_found("Document")
    if document.application_id:
        app = await session.get(Application, document.application_id)
        if app and not await can_access_job(session, user, app.job_id):
            raise _not_found("Document")

    profile = await session.scalar(
        select(ParsedProfile).where(ParsedProfile.document_id == document_id)
    )
    if profile is not None:
        profile.parse_status = ParseStatus.PENDING
        profile.error = None
    await session.commit()
    try:
        process_document.delay(str(document_id))
    except Exception:
        logger.exception("reprocess_enqueue_failed document_id=%s", document_id)
        # Fall back to inline processing so the UI can still recover in dev.
        with sync_session() as sync:
            process_document_sync(sync, document_id)
        return ReprocessOut(document_id=document_id, status="done")
    return ReprocessOut(document_id=document_id, status="queued")


async def patch_parsed_profile(
    session: AsyncSession, user: User, profile_id: uuid.UUID, body: ParsedProfilePatch
) -> ParsedProfileOut:
    profile = await session.get(ParsedProfile, profile_id)
    if profile is None:
        raise _not_found("Parsed profile")
    candidate = await session.get(Candidate, profile.candidate_id)
    if candidate is None or candidate.org_id != user.org_id or candidate.deleted_at is not None:
        raise _not_found("Parsed profile")

    merged: dict[str, Any] = dict(profile.corrected_data or {})
    merged.update(body.data)
    if body.total_experience_years is not None:
        profile.total_experience_years = body.total_experience_years
        merged["total_experience_years"] = float(body.total_experience_years)
    profile.corrected_data = merged
    application_ids = list(
        await session.scalars(
            select(Application.id).where(Application.candidate_id == candidate.id)
        )
    )
    session.add(
        ActivityLog(
            candidate_id=candidate.id,
            actor_id=user.id,
            action="cv.corrected",
            meta={"parsed_profile_id": str(profile_id)},
        )
    )
    await session.commit()

    # Re-score on a sync session after the correction is durable.
    with sync_session() as sync:
        sync_profile = sync.get(ParsedProfile, profile_id)
        if sync_profile is not None:
            for app_id in application_ids:
                app = sync.get(Application, app_id)
                if app is not None:
                    score_application(sync, app, sync_profile)

    await session.refresh(profile)
    return ParsedProfileOut(
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


async def enqueue_job_rescore(session: AsyncSession, user: User, job_id: uuid.UUID) -> RescoreOut:
    if not await can_access_job(session, user, job_id):
        raise _not_found("Job")
    job = await session.get(Job, job_id)
    if job is None or job.deleted_at is not None:
        raise _not_found("Job")
    try:
        rescore_job.delay(str(job_id))
    except Exception:
        logger.exception("rescore_enqueue_failed job_id=%s", job_id)
        with sync_session() as sync:
            from app.services.cv_processing import rescore_job_sync

            rescore_job_sync(sync, job_id)
        return RescoreOut(job_id=job_id, status="done")
    return RescoreOut(job_id=job_id, status="queued")


async def create_manual_candidate(
    session: AsyncSession,
    user: User,
    body: ManualCandidateCreate,
    cv_bytes: bytes | None,
    cv_file_name: str | None,
) -> ManualCandidateResult:
    """CAND-10: HR adds a candidate (and optional application) with CV upload."""
    email = body.email.lower()
    existing = await session.scalar(
        select(Candidate).where(
            Candidate.org_id == user.org_id,
            Candidate.email == email,
            Candidate.deleted_at.is_(None),
        )
    )
    from app.services.salary import apply_salary, candidate_budget

    candidate = existing or Candidate(org_id=user.org_id, email=email)
    candidate.first_name = body.first_name
    candidate.last_name = body.last_name
    if body.phone:
        candidate.phone = body.phone
    if body.current_location:
        candidate.current_location = body.current_location
    if body.current_company:
        candidate.current_company = body.current_company
    if body.current_title:
        candidate.current_title = body.current_title
    if body.total_experience_years is not None:
        candidate.total_experience_years = body.total_experience_years
    if body.notice_period_days is not None:
        candidate.notice_period_days = body.notice_period_days
    if body.linkedin_url:
        candidate.linkedin_url = body.linkedin_url
    if body.portfolio_url:
        candidate.portfolio_url = body.portfolio_url
    if body.department_id is not None:
        candidate.department_id = body.department_id
    apply_salary(candidate, "current", body.current_ctc)
    apply_salary(candidate, "expected", body.expected_ctc)
    apply_salary(candidate, "offered", body.offered_ctc)
    candidate.source = body.source or CandidateSource.MANUAL
    if body.tags:
        candidate.tags = list(dict.fromkeys([*(candidate.tags or []), *body.tags]))
    if existing is None:
        session.add(candidate)
    await session.flush()
    session.add(
        ActivityLog(
            candidate_id=candidate.id,
            actor_id=user.id,
            action="candidate.created_manual" if existing is None else "candidate.updated_manual",
            meta={
                "source": body.source.value if body.source else "manual",
                "reused": existing is not None,
            },
        )
    )

    application_id = None
    reference_no = None
    document_id = None
    job_for_budget: Job | None = None

    if body.job_id is not None:
        if not await can_access_job(session, user, body.job_id):
            raise _not_found("Job")
        job = await session.get(Job, body.job_id)
        if job is None or job.deleted_at is not None:
            raise _not_found("Job")
        job_for_budget = job
        dup = await session.scalar(
            select(Application.id).where(
                Application.candidate_id == candidate.id, Application.job_id == job.id
            )
        )
        if dup is None:
            from app.models.candidate import APPLICATION_REFERENCE_SEQ

            stage = await _applied_stage(session, user.org_id)
            now = datetime.now(UTC)
            sequence = int(
                await session.scalar(select(APPLICATION_REFERENCE_SEQ.next_value())) or 0
            )
            reference_no = f"APP-{now.year}-{sequence:06d}"
            application = Application(
                candidate_id=candidate.id,
                job_id=job.id,
                stage_id=stage.id,
                reference_no=reference_no,
                status=ApplicationStatus.ACTIVE,
                applied_at=now,
                stage_entered_at=now,
                assigned_recruiter_id=user.id,
            )
            session.add(application)
            await session.flush()
            application_id = application.id
            session.add(
                ActivityLog(
                    candidate_id=candidate.id,
                    application_id=application_id,
                    actor_id=user.id,
                    action="application.created",
                    meta={"job_id": str(job.id), "reference_no": reference_no},
                )
            )

    if cv_bytes:
        validated = validate_cv(cv_bytes)
        document_id = uuid.uuid4()
        storage_key = f"{user.org_id}/{candidate.id}/{document_id}.{validated.extension}"
        await session.execute(
            update(Document)
            .where(Document.candidate_id == candidate.id, Document.type == DocumentType.CV)
            .values(is_primary=False)
        )
        session.add_all(
            [
                Document(
                    id=document_id,
                    candidate_id=candidate.id,
                    application_id=application_id,
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
                    application_id=application_id,
                    actor_id=user.id,
                    action="document.uploaded",
                    meta={"type": "cv", "file_name": cv_file_name},
                ),
            ]
        )
        await session.flush()
        await storage.put_object(storage_key, cv_bytes, validated.mime_type)

    await session.commit()
    if document_id is not None:
        try:
            process_document.delay(str(document_id))
        except Exception:
            logger.exception("manual_candidate_process_enqueue_failed")
    return ManualCandidateResult(
        candidate_id=candidate.id,
        application_id=application_id,
        document_id=document_id,
        reference_no=reference_no,
        reused=existing is not None,
        budget_status=(
            candidate_budget(candidate, job_for_budget.salary_max, job_for_budget.salary_min)
            if job_for_budget is not None
            else candidate_budget(candidate, None)
        ),
    )


async def parse_cv_preview(cv_bytes: bytes, file_name: str | None) -> CvParseOut:
    """Extract autofill fields from a CV without saving anything."""
    from app.cv_engine import RuleBasedParser, extract_text

    validated = validate_cv(cv_bytes)
    extracted = extract_text(cv_bytes, validated.mime_type)
    parsed = RuleBasedParser().parse(extracted.text, file_meta=extracted)
    first_name = None
    last_name = None
    if parsed.full_name:
        parts = parsed.full_name.split()
        first_name = parts[0]
        last_name = " ".join(parts[1:]) if len(parts) > 1 else None
    linkedin = next((u for u in parsed.links if "linkedin.com" in u.lower()), None)
    title = parsed.experience[0].title if parsed.experience else None
    company = parsed.experience[0].company if parsed.experience else None
    return CvParseOut(
        file_name=file_name or f"cv.{validated.extension}",
        first_name=first_name,
        last_name=last_name,
        email=parsed.email,
        phone=parsed.phone,
        current_location=parsed.location,
        current_company=company,
        current_title=title,
        total_experience_years=parsed.total_experience_years,
        linkedin_url=linkedin,
        skills=list(parsed.skills[:40]),
        confidence=dict(parsed.confidence),
    )


async def find_duplicates(
    session: AsyncSession, user: User, *, email: str | None, phone: str | None
) -> DuplicateCheckOut:
    from app.schemas.application import DuplicateMatch

    if not email and not phone:
        return DuplicateCheckOut(matches=[])

    by_id: dict[uuid.UUID, Candidate] = {}
    if email:
        row = await session.scalar(
            select(Candidate).where(
                Candidate.org_id == user.org_id,
                Candidate.email == email.lower(),
                Candidate.deleted_at.is_(None),
            )
        )
        if row is not None:
            by_id[row.id] = row

    phone_digits = "".join(c for c in (phone or "") if c.isdigit())
    if phone_digits:
        # Narrow in SQL, then compare last 10 digits in Python (phones are free-form).
        suffix = phone_digits[-10:]
        phone_rows = list(
            await session.scalars(
                select(Candidate)
                .where(
                    Candidate.org_id == user.org_id,
                    Candidate.deleted_at.is_(None),
                    Candidate.phone.is_not(None),
                    or_(
                        Candidate.phone.contains(suffix),
                        Candidate.phone.contains(phone_digits),
                    ),
                )
                .limit(50)
            )
        )
        for row in phone_rows:
            row_digits = "".join(c for c in (row.phone or "") if c.isdigit())
            if row_digits.endswith(suffix) or phone_digits.endswith(row_digits[-10:]):
                by_id[row.id] = row

    matches: list[DuplicateMatch] = []
    for row in by_id.values():
        matched_on: list[str] = []
        if email and row.email.lower() == email.lower():
            matched_on.append("email")
        row_digits = "".join(c for c in (row.phone or "") if c.isdigit())
        if (
            phone_digits
            and row_digits
            and (row_digits.endswith(phone_digits[-10:]) or phone_digits.endswith(row_digits[-10:]))
        ):
            matched_on.append("phone")
        if not matched_on:
            continue
        matches.append(
            DuplicateMatch(
                id=row.id,
                first_name=row.first_name,
                last_name=row.last_name,
                email=row.email,
                phone=row.phone,
                matched_on=matched_on,
            )
        )
    return DuplicateCheckOut(matches=matches)
