"""Global search (ADM-04)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import scope_jobs_query
from app.models import Candidate, Job, User


async def global_search(session: AsyncSession, user: User, q: str) -> dict[str, list[dict[str, Any]]]:
    query = q.strip()
    if len(query) < 2:
        return {"candidates": [], "jobs": []}

    cand_stmt = (
        select(Candidate)
        .where(
            Candidate.org_id == user.org_id,
            Candidate.deleted_at.is_(None),
            or_(
                Candidate.first_name.icontains(query, autoescape=True),
                Candidate.last_name.icontains(query, autoescape=True),
                Candidate.email.icontains(query, autoescape=True),
            ),
        )
        .limit(10)
    )
    candidates = [
        {
            "id": str(c.id),
            "label": f"{c.first_name} {c.last_name}",
            "email": c.email,
            "type": "candidate",
        }
        for c in await session.scalars(cand_stmt)
    ]

    job_stmt = scope_jobs_query(
        user,
        select(Job)
        .where(Job.deleted_at.is_(None), Job.title.icontains(query, autoescape=True))
        .limit(10),
    )
    jobs = [
        {"id": str(j.id), "label": j.title, "slug": j.slug, "type": "job"}
        for j in await session.scalars(job_stmt)
    ]
    return {"candidates": candidates, "jobs": jobs}
