import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_roles
from app.models import User
from app.models.enums import UserRole
from app.models.interviews import InterviewMode, InterviewType, Recommendation
from app.services import interviews as interviews_service

router = APIRouter(prefix="/api/v1/interviews", tags=["interviews"])
Session = Annotated[AsyncSession, Depends(get_db)]
Scheduler = Annotated[
    User,
    Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER)),
]


class InterviewCreate(BaseModel):
    application_id: uuid.UUID
    round_name: str = Field(min_length=1, max_length=200)
    type: InterviewType
    mode: InterviewMode
    scheduled_at: datetime
    duration_min: int = Field(default=60, ge=15, le=480)
    panel_user_ids: list[uuid.UUID] = Field(default_factory=list)
    meeting_link: str | None = None
    location: str | None = None


class ScorecardIn(BaseModel):
    ratings: dict[str, Any]
    comments: str | None = None
    recommendation: Recommendation


@router.post("")
async def create_interview(
    body: InterviewCreate, user: Scheduler, session: Session
) -> dict[str, Any]:
    return await interviews_service.create_interview(
        session,
        user,
        application_id=body.application_id,
        round_name=body.round_name,
        type=body.type,
        mode=body.mode,
        scheduled_at=body.scheduled_at,
        duration_min=body.duration_min,
        panel_user_ids=body.panel_user_ids,
        meeting_link=body.meeting_link,
        location=body.location,
    )


@router.get("/mine")
async def my_interviews(user: CurrentUser, session: Session) -> list[dict[str, Any]]:
    return await interviews_service.my_interviews(session, user)


@router.post("/{interview_id}/scorecard")
async def submit_scorecard(
    interview_id: uuid.UUID, body: ScorecardIn, user: CurrentUser, session: Session
) -> dict[str, Any]:
    return await interviews_service.submit_scorecard(
        session,
        user,
        interview_id,
        ratings=body.ratings,
        comments=body.comments,
        recommendation=body.recommendation,
    )
