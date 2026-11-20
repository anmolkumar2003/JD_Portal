import hashlib
import logging
import uuid
from datetime import UTC, datetime
from pathlib import PurePath

from fastapi import status
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.errors import AppError
from app.core.rate_limit import enforce_rate_limit
from app.models import (
    ActivityLog,
    Application,
    Candidate,
    Document,
    Job,
    ParsedProfile,
    PipelineStage,
)
from app.models.candidate import APPLICATION_REFERENCE_SEQ
from app.models.enums import DocumentType, StageType
from app.schemas.application import ApplyForm, ApplyResult
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
