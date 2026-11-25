import asyncio
import logging
import smtplib
import uuid
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import get_settings
from app.core.db import SessionLocal, sync_session
from app.services.cv_processing import process_document_sync, rescore_job_sync
from app.services.draft_cleanup import cleanup_expired_drafts_sync
from app.services.retention import run_retention_rejected
from app.services.storage_cleanup import cleanup_orphan_storage_sync
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="ping")
def ping() -> str:
    return "pong"


@celery_app.task(
    name="send_email",
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    max_retries=3,
)
def send_email(to: str, subject: str, body: str) -> None:
    """Send a plain-text email over SMTP (Mailpit in development)."""
    settings = get_settings()
    message = EmailMessage()
    message["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_user and settings.smtp_password:
            smtp.login(settings.smtp_user, settings.smtp_password.get_secret_value())
        smtp.send_message(message)


@celery_app.task(
    name="process_document",
    bind=True,
    autoretry_for=(OSError, RuntimeError, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
)
def process_document(self: object, document_id: str) -> dict[str, str]:
    """CV-07: extract, parse, ATS check, match for all applications of the candidate."""
    doc_uuid = uuid.UUID(document_id)
    logger.info("process_document_start document_id=%s", document_id)
    with sync_session() as session:
        process_document_sync(session, doc_uuid)
    return {"document_id": document_id, "status": "done"}


@celery_app.task(
    name="rescore_job",
    bind=True,
    autoretry_for=(OSError, RuntimeError, ConnectionError),
    retry_backoff=True,
    max_retries=3,
)
def rescore_job(self: object, job_id: str) -> dict[str, int | str]:
    job_uuid = uuid.UUID(job_id)
    with sync_session() as session:
        count = rescore_job_sync(session, job_uuid)
    return {"job_id": job_id, "rescored": count}


@celery_app.task(name="run_retention_rejected")
def run_retention_rejected_task() -> dict[str, int | bool | str]:
    async def _run() -> dict[str, int | bool | str]:
        async with SessionLocal() as session:
            return await run_retention_rejected(session)

    return asyncio.run(_run())


@celery_app.task(name="cleanup_orphan_storage")
def cleanup_orphan_storage() -> dict[str, int]:
    """Retry MinIO deletes that failed after a candidate hard-delete (runs hourly)."""
    with sync_session() as session:
        return cleanup_orphan_storage_sync(session)


@celery_app.task(name="cleanup_expired_drafts")
def cleanup_expired_drafts() -> dict[str, int]:
    """Delete Add Candidate drafts older than 24h together with their MinIO objects (hourly)."""
    with sync_session() as session:
        return cleanup_expired_drafts_sync(session)
