import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.schemas.application import DownloadUrlOut
from app.services import documents as documents_service

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("/{document_id}/download-url", response_model=DownloadUrlOut)
async def get_download_url(
    document_id: uuid.UUID, user: CurrentUser, session: Session
) -> DownloadUrlOut:
    return await documents_service.get_download_url(session, user, document_id)
