import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.application import DownloadUrlOut, ReprocessOut
from app.services import analysis as analysis_service
from app.services import documents as documents_service

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

Session = Annotated[AsyncSession, Depends(get_db)]
ReprocessUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER, UserRole.HIRING_MANAGER
        )
    ),
]


@router.get("/{document_id}/download-url", response_model=DownloadUrlOut)
async def get_download_url(
    document_id: uuid.UUID, user: CurrentUser, session: Session
) -> DownloadUrlOut:
    return await documents_service.get_download_url(session, user, document_id)


@router.post("/{document_id}/reprocess", response_model=ReprocessOut)
async def reprocess_document(
    document_id: uuid.UUID, user: ReprocessUser, session: Session
) -> ReprocessOut:
    return await analysis_service.reprocess_document(session, user, document_id)
