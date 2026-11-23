import hashlib
import logging
import uuid

from fastapi import status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.deps import ORG_WIDE_JOB_ROLES, can_access_job
from app.core.errors import AppError
from app.models import ActivityLog, Application, Candidate, Document, ParsedProfile, User
from app.models.enums import DocumentType
from app.schemas.application import DocumentOut, DownloadUrlOut
from app.services.applications import _safe_file_name
from app.services.cv_validation import validate_cv
from app.workers.tasks import process_document

logger = logging.getLogger(__name__)

DOWNLOAD_URL_TTL_SECONDS = 300


async def get_download_url(
    session: AsyncSession, user: User, document_id: uuid.UUID
) -> DownloadUrlOut:
    """Signed, short-lived link; 404 for documents outside the user's org or job access."""
    row = (
        await session.execute(
            select(Document, Candidate.org_id, Application.job_id)
            .join(Candidate, Candidate.id == Document.candidate_id)
            .outerjoin(Application, Application.id == Document.application_id)
            .where(Document.id == document_id, Candidate.deleted_at.is_(None))
        )
    ).first()
    not_found = AppError(status.HTTP_404_NOT_FOUND, "not_found", "Document not found")
    if row is None:
        raise not_found
    document, org_id, job_id = row
    if org_id != user.org_id:
        raise not_found
    if job_id is None:
        if user.role not in ORG_WIDE_JOB_ROLES:
            raise not_found
    elif not await can_access_job(session, user, job_id):
        raise not_found

    url = storage.presigned_download_url(
        document.storage_key, document.file_name, DOWNLOAD_URL_TTL_SECONDS
    )
    return DownloadUrlOut(
        url=url, expires_in=DOWNLOAD_URL_TTL_SECONDS, file_name=document.file_name
    )


async def upload_candidate_document(
    session: AsyncSession,
    user: User,
    *,
    candidate_id: uuid.UUID,
    file_bytes: bytes,
    file_name: str | None,
    doc_type: DocumentType,
    application_id: uuid.UUID | None,
) -> DocumentOut:
    """Store a document on an existing candidate and queue parsing for CVs."""
    candidate = await session.scalar(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.org_id == user.org_id,
            Candidate.deleted_at.is_(None),
        )
    )
    if candidate is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Candidate not found")
    if application_id is not None:
        application = await session.get(Application, application_id)
        if application is None or application.candidate_id != candidate.id:
            raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Application not found")
        if not await can_access_job(session, user, application.job_id):
            raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Application not found")

    validated = validate_cv(file_bytes)
    document_id = uuid.uuid4()
    storage_key = f"{user.org_id}/{candidate.id}/{document_id}.{validated.extension}"
    if doc_type == DocumentType.CV:
        await session.execute(
            update(Document)
            .where(Document.candidate_id == candidate.id, Document.type == DocumentType.CV)
            .values(is_primary=False)
        )
    document = Document(
        id=document_id,
        candidate_id=candidate.id,
        application_id=application_id,
        type=doc_type,
        file_name=_safe_file_name(file_name, validated.extension),
        mime_type=validated.mime_type,
        size=len(file_bytes),
        storage_key=storage_key,
        checksum=hashlib.sha256(file_bytes).hexdigest(),
        is_primary=doc_type == DocumentType.CV,
        virus_scan_status=validated.virus_scan_status,
    )
    session.add(document)
    if doc_type == DocumentType.CV:
        session.add(ParsedProfile(document_id=document_id, candidate_id=candidate.id))
    session.add(
        ActivityLog(
            candidate_id=candidate.id,
            application_id=application_id,
            actor_id=user.id,
            action="document.uploaded",
            meta={"type": doc_type.value, "file_name": document.file_name},
        )
    )
    await session.flush()
    await storage.put_object(storage_key, file_bytes, validated.mime_type)
    await session.commit()
    await session.refresh(document)
    if doc_type == DocumentType.CV:
        try:
            process_document.delay(str(document_id))
        except Exception:
            logger.exception("document_process_enqueue_failed")
    return DocumentOut.model_validate(document)


async def delete_document(session: AsyncSession, user: User, document_id: uuid.UUID) -> None:
    """Remove a document row and its object storage blob (recruiter+)."""
    row = (
        await session.execute(
            select(Document, Candidate.org_id, Application.job_id)
            .join(Candidate, Candidate.id == Document.candidate_id)
            .outerjoin(Application, Application.id == Document.application_id)
            .where(Document.id == document_id, Candidate.deleted_at.is_(None))
        )
    ).first()
    not_found = AppError(status.HTTP_404_NOT_FOUND, "not_found", "Document not found")
    if row is None:
        raise not_found
    document, org_id, job_id = row
    if org_id != user.org_id:
        raise not_found
    if job_id is None:
        if user.role not in ORG_WIDE_JOB_ROLES:
            raise not_found
    elif not await can_access_job(session, user, job_id):
        raise not_found

    storage_key = document.storage_key
    candidate_id = document.candidate_id
    application_id = document.application_id
    file_name = document.file_name
    await session.delete(document)
    session.add(
        ActivityLog(
            candidate_id=candidate_id,
            application_id=application_id,
            actor_id=user.id,
            action="document.deleted",
            meta={"file_name": file_name},
        )
    )
    await session.commit()
    try:
        await storage.delete_object(storage_key)
    except Exception:
        logger.exception("document_storage_delete_failed key=%s", storage_key)


async def rename_document(
    session: AsyncSession, user: User, document_id: uuid.UUID, file_name: str
) -> DocumentOut:
    """Update the display file name for a document."""
    row = (
        await session.execute(
            select(Document, Candidate.org_id, Application.job_id)
            .join(Candidate, Candidate.id == Document.candidate_id)
            .outerjoin(Application, Application.id == Document.application_id)
            .where(Document.id == document_id, Candidate.deleted_at.is_(None))
        )
    ).first()
    not_found = AppError(status.HTTP_404_NOT_FOUND, "not_found", "Document not found")
    if row is None:
        raise not_found
    document, org_id, job_id = row
    if org_id != user.org_id:
        raise not_found
    if job_id is None:
        if user.role not in ORG_WIDE_JOB_ROLES:
            raise not_found
    elif not await can_access_job(session, user, job_id):
        raise not_found

    safe = _safe_file_name(file_name, document.file_name.rsplit(".", 1)[-1])
    document.file_name = safe
    session.add(
        ActivityLog(
            candidate_id=document.candidate_id,
            application_id=document.application_id,
            actor_id=user.id,
            action="document.renamed",
            meta={"file_name": safe},
        )
    )
    await session.commit()
    await session.refresh(document)
    return DocumentOut.model_validate(document)
