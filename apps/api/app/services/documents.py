import uuid

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.deps import ORG_WIDE_JOB_ROLES, can_access_job
from app.core.errors import AppError
from app.models import Application, Candidate, Document, User
from app.schemas.application import DownloadUrlOut

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
