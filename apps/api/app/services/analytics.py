"""Dashboard analytics (DASH-01..04)."""

from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import Select, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from app.core.deps import scope_jobs_query
from app.models import Application, Candidate, Interview, Job, PipelineStage, User
from app.models.enums import ApplicationStatus, JobStatus
from app.models.hiring import Offer, OfferStatus
from app.models.interviews import InterviewStatus


async def overview(
    session: AsyncSession, user: User, *, start: date | None = None, end: date | None = None
) -> dict[str, Any]:
    today = datetime.now(UTC).date()
    week_ago = today - timedelta(days=7)
    month_start = today.replace(day=1)

    jobs_stmt: Select[Any] = scope_jobs_query(
        user, select(func.count()).select_from(Job).where(Job.deleted_at.is_(None))
    )
    open_jobs = int(
        await session.scalar(jobs_stmt.where(Job.status == JobStatus.OPEN)) or 0
    )

    app_base = (
        select(Application)
        .join(Job, Job.id == Application.job_id)
        .join(Candidate, Candidate.id == Application.candidate_id)
        .where(Candidate.deleted_at.is_(None))
    )
    app_base = scope_jobs_query(user, app_base)

    total_applicants = int(
        await session.scalar(select(func.count()).select_from(app_base.subquery())) or 0
    )
    new_this_week = int(
        await session.scalar(
            select(func.count()).select_from(
                app_base.where(Application.applied_at >= datetime.combine(week_ago, datetime.min.time(), tzinfo=UTC)).subquery()
            )
        )
        or 0
    )

    interviews_today = 0
    try:
        interviews_today = int(
            await session.scalar(
                select(func.count())
                .select_from(Interview)
                .where(
                    cast(Interview.scheduled_at, Date) == today,
                    Interview.status == InterviewStatus.SCHEDULED,
                )
            )
            or 0
        )
    except Exception:  # table may not exist until migration
        interviews_today = 0

    offers_pending = 0
    try:
        offers_pending = int(
            await session.scalar(
                select(func.count())
                .select_from(Offer)
                .where(Offer.status == OfferStatus.PENDING_APPROVAL)
            )
            or 0
        )
    except Exception:
        offers_pending = 0

    hires_month = int(
        await session.scalar(
            select(func.count()).select_from(
                app_base.where(
                    Application.status == ApplicationStatus.HIRED,
                    Application.stage_entered_at
                    >= datetime.combine(month_start, datetime.min.time(), tzinfo=UTC),
                ).subquery()
            )
        )
        or 0
    )

    return {
        "open_jobs": open_jobs,
        "total_applicants": total_applicants,
        "new_this_week": new_this_week,
        "interviews_today": interviews_today,
        "offers_pending": offers_pending,
        "hires_this_month": hires_month,
        "range": {"start": start.isoformat() if start else None, "end": end.isoformat() if end else None},
    }


async def funnel(session: AsyncSession, user: User) -> list[dict[str, Any]]:
    stages = await session.scalars(
        select(PipelineStage).where(PipelineStage.org_id == user.org_id).order_by(PipelineStage.order)
    )
    result: list[dict[str, Any]] = []
    for stage in stages:
        stmt = (
            select(func.count())
            .select_from(Application)
            .join(Job, Job.id == Application.job_id)
            .where(Application.stage_id == stage.id)
        )
        stmt = scope_jobs_query(user, stmt)
        count = int(await session.scalar(stmt) or 0)
        result.append({"stage": stage.name, "type": stage.type.value, "count": count})
    return result


async def sources(session: AsyncSession, user: User) -> list[dict[str, Any]]:
    stmt = (
        select(Candidate.source, func.count())
        .join(Application, Application.candidate_id == Candidate.id)
        .join(Job, Job.id == Application.job_id)
        .where(Candidate.deleted_at.is_(None))
        .group_by(Candidate.source)
    )
    stmt = scope_jobs_query(user, stmt)
    rows = (await session.execute(stmt)).all()
    return [{"source": str(src.value if hasattr(src, "value") else src), "count": int(cnt)} for src, cnt in rows]


async def applications_over_time(session: AsyncSession, user: User, days: int = 30) -> list[dict[str, Any]]:
    start = datetime.now(UTC) - timedelta(days=days)
    stmt = (
        select(cast(Application.applied_at, Date).label("day"), func.count())
        .join(Job, Job.id == Application.job_id)
        .where(Application.applied_at >= start)
        .group_by("day")
        .order_by("day")
    )
    stmt = scope_jobs_query(user, stmt)
    rows = (await session.execute(stmt)).all()
    return [{"date": d.isoformat(), "count": int(c)} for d, c in rows]


async def export_csv(session: AsyncSession, user: User) -> str:
    items = await funnel(session, user)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["stage", "type", "count"])
    writer.writeheader()
    writer.writerows(items)
    return buf.getvalue()
