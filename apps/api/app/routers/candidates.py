import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.schemas.application import TimelineEntry
from app.services import applications as applications_service

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])

Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("/{candidate_id}/timeline", response_model=list[TimelineEntry])
async def candidate_timeline(
    candidate_id: uuid.UUID, user: CurrentUser, session: Session
) -> list[TimelineEntry]:
    return await applications_service.candidate_timeline(session, user, candidate_id)
