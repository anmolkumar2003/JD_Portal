import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, StringConstraints
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.application import DocumentOut, DownloadUrlOut, ReprocessOut
from app.services import analysis as analysis_service
from app.services import documents as documents_service

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

Session = Annotated[AsyncSession, Depends(get_db)]
Editor = Annotated[
    User,
    Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER)),
]
ReprocessUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER, UserRole.HIRING_MANAGER
        )
    ),
]


class DocumentRenameIn(BaseModel):
    file_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
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


@router.patch("/{document_id}", response_model=DocumentOut)
async def rename_document(
    document_id: uuid.UUID, body: DocumentRenameIn, user: Editor, session: Session
) -> DocumentOut:
    return await documents_service.rename_document(session, user, document_id, body.file_name)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: uuid.UUID, user: Editor, session: Session) -> Response:
    await documents_service.delete_document(session, user, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
