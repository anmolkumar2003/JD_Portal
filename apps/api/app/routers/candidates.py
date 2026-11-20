import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.schemas.candidate import TimelineEvent
from app.services import candidates as candidates_service

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])

Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("/{candidate_id}/timeline", response_model=list[TimelineEvent])
async def get_timeline(
    candidate_id: uuid.UUID, user: CurrentUser, session: Session
) -> list[TimelineEvent]:
    return await candidates_service.get_timeline(session, user, candidate_id)
