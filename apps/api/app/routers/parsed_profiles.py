import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.application import ParsedProfileOut, ParsedProfilePatch
from app.services import analysis as analysis_service

router = APIRouter(prefix="/api/v1/parsed-profiles", tags=["parsed-profiles"])

Session = Annotated[AsyncSession, Depends(get_db)]
Editor = Annotated[
    User,
    Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER)),
]


@router.patch("/{profile_id}", response_model=ParsedProfileOut)
async def patch_parsed_profile(
    profile_id: uuid.UUID, body: ParsedProfilePatch, user: Editor, session: Session
) -> ParsedProfileOut:
    return await analysis_service.patch_parsed_profile(session, user, profile_id, body)
