import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import AdminUser, CurrentUser, require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.ratings import (
    FinalScoreOut,
    InterviewRatingIn,
    InterviewRatingOut,
    ScoringWeights,
)
from app.services import ratings as ratings_service

router = APIRouter(tags=["ratings"])

Session = Annotated[AsyncSession, Depends(get_db)]
Editor = Annotated[
    User,
    Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER)),
]


@router.get(
    "/api/v1/applications/{application_id}/ratings", response_model=list[InterviewRatingOut]
)
async def list_ratings(
    application_id: uuid.UUID, user: CurrentUser, session: Session
) -> list[InterviewRatingOut]:
    return await ratings_service.list_ratings(session, user, application_id)


@router.post(
    "/api/v1/applications/{application_id}/ratings",
    response_model=InterviewRatingOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_rating(
    application_id: uuid.UUID, body: InterviewRatingIn, user: Editor, session: Session
) -> InterviewRatingOut:
    return await ratings_service.create_rating(session, user, application_id, body)


@router.get("/api/v1/applications/{application_id}/final-score", response_model=FinalScoreOut)
async def final_score(
    application_id: uuid.UUID, user: CurrentUser, session: Session
) -> FinalScoreOut:
    return await ratings_service.final_score_panel(session, user, application_id)


@router.patch("/api/v1/ratings/{rating_id}", response_model=InterviewRatingOut)
async def update_rating(
    rating_id: uuid.UUID, body: InterviewRatingIn, user: Editor, session: Session
) -> InterviewRatingOut:
    return await ratings_service.update_rating(session, user, rating_id, body)


@router.delete("/api/v1/ratings/{rating_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rating(rating_id: uuid.UUID, user: Editor, session: Session) -> Response:
    await ratings_service.delete_rating(session, user, rating_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/v1/org/scoring-weights", response_model=ScoringWeights)
async def get_weights(user: CurrentUser, session: Session) -> ScoringWeights:
    return await ratings_service.get_scoring_weights(session, user)


@router.put("/api/v1/org/scoring-weights", response_model=ScoringWeights)
async def put_weights(body: ScoringWeights, user: AdminUser, session: Session) -> ScoringWeights:
    return await ratings_service.set_scoring_weights(session, user, body)
