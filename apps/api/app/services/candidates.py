import uuid

from fastapi import status
from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import job_access_clause
from app.core.errors import AppError
from app.models import ActivityLog, Application, Candidate, Job, User
from app.schemas.candidate import TimelineActor, TimelineEvent


async def _ensure_candidate_access(
    session: AsyncSession, user: User, candidate_id: uuid.UUID
) -> Candidate:
    """Candidate is visible if the user can access at least one of their applications' jobs."""
    candidate = await session.scalar(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.org_id == user.org_id,
            Candidate.deleted_at.is_(None),
        )
    )
    if candidate is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Candidate not found")

    has_access = await session.scalar(
        select(
            exists().where(
                Application.candidate_id == candidate.id,
                Application.job_id == Job.id,
                Job.org_id == user.org_id,
                Job.deleted_at.is_(None),
                job_access_clause(user),
            )
        )
    )
    if not has_access:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Candidate not found")
    return candidate


async def get_timeline(
    session: AsyncSession, user: User, candidate_id: uuid.UUID
) -> list[TimelineEvent]:
    await _ensure_candidate_access(session, user, candidate_id)

    # Only surface events for applications the user may see (or candidate-level with no app).
    accessible_apps = (
        select(Application.id)
        .join(Job, Job.id == Application.job_id)
        .where(
            Application.candidate_id == candidate_id,
            Job.org_id == user.org_id,
            Job.deleted_at.is_(None),
            job_access_clause(user),
        )
    )

    rows = (
        await session.execute(
            select(ActivityLog, User)
            .outerjoin(User, User.id == ActivityLog.actor_id)
            .where(
                ActivityLog.candidate_id == candidate_id,
                or_(
                    ActivityLog.application_id.is_(None),
                    ActivityLog.application_id.in_(accessible_apps),
                ),
            )
            .order_by(ActivityLog.occurred_at.desc())
        )
    ).all()

    events: list[TimelineEvent] = []
    for log, actor in rows:
        events.append(
            TimelineEvent(
                id=log.id,
                action=log.action,
                occurred_at=log.occurred_at,
                application_id=log.application_id,
                actor=TimelineActor(id=actor.id, full_name=actor.full_name) if actor else None,
                meta=log.meta or {},
            )
        )
    return events
