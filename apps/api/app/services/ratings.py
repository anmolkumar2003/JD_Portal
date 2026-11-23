"""CRUD for simple interview ratings and advisory final-score helpers."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import can_access_job
from app.core.errors import AppError
from app.models import (
    ActivityLog,
    Application,
    AtsCheck,
    Candidate,
    Document,
    MatchResult,
    User,
)
from app.models.ratings import InterviewRating
from app.schemas.ratings import (
    FinalScoreOut,
    InterviewRatingIn,
    InterviewRatingOut,
    ScoringWeights,
)
from app.services.org import _user_org

SCORING_KEY = "scoring_weights"


def _not_found(entity: str = "Rating") -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "not_found", f"{entity} not found")


def _out(row: InterviewRating) -> InterviewRatingOut:
    return InterviewRatingOut(
        id=row.id,
        application_id=row.application_id,
        round_name=row.round_name,
        interviewed_at=row.interviewed_at,
        interviewer_name=row.interviewer_name,
        interviewer_id=row.interviewer_id,
        mode=row.mode,
        comments=row.comments,
        skill_ratings=list(row.skill_ratings or []),
        overall_rating=row.overall_rating,
        recommendation=row.recommendation,
        strengths=row.strengths,
        concerns=row.concerns,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _scoped_application(
    session: AsyncSession, user: User, application_id: uuid.UUID
) -> Application:
    application = await session.get(Application, application_id)
    if application is None:
        raise _not_found("Application")
    candidate = await session.get(Candidate, application.candidate_id)
    if candidate is None or candidate.org_id != user.org_id or candidate.deleted_at is not None:
        raise _not_found("Application")
    if not await can_access_job(session, user, application.job_id):
        raise _not_found("Application")
    return application


def scoring_weights_from_org(settings: dict[str, object] | None) -> ScoringWeights:
    raw = (settings or {}).get(SCORING_KEY) or {}
    if not isinstance(raw, dict):
        return ScoringWeights()
    try:
        return ScoringWeights(
            match_weight=int(raw.get("match_weight", 50)),
            interview_weight=int(raw.get("interview_weight", 50)),
        )
    except (TypeError, ValueError):
        return ScoringWeights()


async def get_scoring_weights(session: AsyncSession, user: User) -> ScoringWeights:
    org = await _user_org(session, user)
    return scoring_weights_from_org(org.settings)


async def set_scoring_weights(
    session: AsyncSession, user: User, weights: ScoringWeights
) -> ScoringWeights:
    org = await _user_org(session, user)
    settings = dict(org.settings or {})
    settings[SCORING_KEY] = weights.model_dump()
    org.settings = settings
    await session.commit()
    return weights


async def list_ratings(
    session: AsyncSession, user: User, application_id: uuid.UUID
) -> list[InterviewRatingOut]:
    await _scoped_application(session, user, application_id)
    rows = list(
        await session.scalars(
            select(InterviewRating)
            .where(InterviewRating.application_id == application_id)
            .order_by(InterviewRating.interviewed_at.desc())
        )
    )
    return [_out(r) for r in rows]


async def create_rating(
    session: AsyncSession, user: User, application_id: uuid.UUID, body: InterviewRatingIn
) -> InterviewRatingOut:
    application = await _scoped_application(session, user, application_id)
    row = InterviewRating(
        org_id=user.org_id,
        application_id=application.id,
        round_name=body.round_name,
        interviewed_at=body.interviewed_at,
        interviewer_name=body.interviewer_name,
        interviewer_id=body.interviewer_id,
        mode=body.mode,
        comments=body.comments,
        skill_ratings=[s.model_dump() for s in body.skill_ratings],
        overall_rating=body.overall_rating,
        recommendation=body.recommendation,
        strengths=body.strengths,
        concerns=body.concerns,
        created_by=user.id,
    )
    session.add(row)
    await session.flush()
    session.add(
        ActivityLog(
            candidate_id=application.candidate_id,
            application_id=application.id,
            actor_id=user.id,
            action="interview_rating.created",
            meta={"rating_id": str(row.id), "overall": body.overall_rating},
        )
    )
    await _refresh_application_avg(session, application)
    await session.commit()
    await session.refresh(row)
    return _out(row)


async def update_rating(
    session: AsyncSession, user: User, rating_id: uuid.UUID, body: InterviewRatingIn
) -> InterviewRatingOut:
    row = await session.get(InterviewRating, rating_id)
    if row is None or row.org_id != user.org_id:
        raise _not_found()
    application = await _scoped_application(session, user, row.application_id)
    row.round_name = body.round_name
    row.interviewed_at = body.interviewed_at
    row.interviewer_name = body.interviewer_name
    row.interviewer_id = body.interviewer_id
    row.mode = body.mode
    row.comments = body.comments
    row.skill_ratings = [s.model_dump() for s in body.skill_ratings]
    row.overall_rating = body.overall_rating
    row.recommendation = body.recommendation
    row.strengths = body.strengths
    row.concerns = body.concerns
    session.add(
        ActivityLog(
            candidate_id=application.candidate_id,
            application_id=application.id,
            actor_id=user.id,
            action="interview_rating.updated",
            meta={"rating_id": str(row.id)},
        )
    )
    await _refresh_application_avg(session, application)
    await session.commit()
    await session.refresh(row)
    return _out(row)


async def delete_rating(session: AsyncSession, user: User, rating_id: uuid.UUID) -> None:
    row = await session.get(InterviewRating, rating_id)
    if row is None or row.org_id != user.org_id:
        raise _not_found()
    application = await _scoped_application(session, user, row.application_id)
    session.add(
        ActivityLog(
            candidate_id=application.candidate_id,
            application_id=application.id,
            actor_id=user.id,
            action="interview_rating.deleted",
            meta={"rating_id": str(row.id)},
        )
    )
    await session.delete(row)
    await session.flush()
    await _refresh_application_avg(session, application)
    await session.commit()


async def _refresh_application_avg(session: AsyncSession, application: Application) -> None:
    avg = await session.scalar(
        select(func.avg(InterviewRating.overall_rating)).where(
            InterviewRating.application_id == application.id
        )
    )
    application.overall_rating = Decimal(str(round(float(avg), 2))) if avg is not None else None


async def average_rating(session: AsyncSession, application_id: uuid.UUID) -> float | None:
    avg = await session.scalar(
        select(func.avg(InterviewRating.overall_rating)).where(
            InterviewRating.application_id == application_id
        )
    )
    return round(float(avg), 2) if avg is not None else None


async def final_score_panel(
    session: AsyncSession, user: User, application_id: uuid.UUID
) -> FinalScoreOut:
    application = await _scoped_application(session, user, application_id)
    weights = await get_scoring_weights(session, user)
    match = await session.scalar(
        select(MatchResult)
        .where(MatchResult.application_id == application.id)
        .order_by(MatchResult.computed_at.desc())
        .limit(1)
    )
    ats = await session.scalar(
        select(AtsCheck)
        .join(Document, Document.id == AtsCheck.document_id)
        .where(Document.candidate_id == application.candidate_id)
        .order_by(AtsCheck.created_at.desc())
        .limit(1)
    )
    interview_avg = await average_rating(session, application.id)
    match_score = match.overall_score if match is not None else None
    ats_score = ats.score if ats is not None else None

    final: float | None = None
    if match_score is not None or interview_avg is not None:
        # Interview ratings are 1-5; scale to 0-100 to combine with match score.
        interview_100 = (interview_avg * 20) if interview_avg is not None else None
        parts: list[tuple[float, int]] = []
        if match_score is not None and weights.match_weight:
            parts.append((float(match_score), weights.match_weight))
        if interview_100 is not None and weights.interview_weight:
            parts.append((interview_100, weights.interview_weight))
        if parts:
            total_w = sum(w for _, w in parts)
            final = round(sum(score * w for score, w in parts) / total_w, 1)

    return FinalScoreOut(
        match_score=match_score,
        ats_score=ats_score,
        interview_avg=interview_avg,
        weights=weights,
        final_score=final,
    )
