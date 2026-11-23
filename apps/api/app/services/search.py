"""Global search (ADM-04) — trigram-aware candidate and job lookup for Cmd+K."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import scope_jobs_query
from app.models import Candidate, Job, User


async def global_search(
    session: AsyncSession, user: User, q: str
) -> dict[str, list[dict[str, Any]]]:
    query = q.strip()
    if len(query) < 2:
        return {"candidates": [], "jobs": []}

    name_sim = func.greatest(
        func.similarity(Candidate.first_name, query),
        func.similarity(Candidate.last_name, query),
        func.similarity(func.concat(Candidate.first_name, " ", Candidate.last_name), query),
    )
    cand_stmt = (
        select(Candidate)
        .where(
            Candidate.org_id == user.org_id,
            Candidate.deleted_at.is_(None),
            or_(
                name_sim > 0.25,
                Candidate.first_name.icontains(query, autoescape=True),
                Candidate.last_name.icontains(query, autoescape=True),
                Candidate.email.icontains(query, autoescape=True),
                Candidate.phone.icontains(query, autoescape=True),
            ),
        )
        .order_by(name_sim.desc())
        .limit(10)
    )
    candidates = [
        {
            "id": str(c.id),
            "label": f"{c.first_name} {c.last_name}",
            "email": c.email,
            "type": "candidate",
            "href": f"/candidates/{c.id}",
        }
        for c in await session.scalars(cand_stmt)
    ]

    job_sim = func.similarity(Job.title, query)
    job_stmt = scope_jobs_query(
        user,
        select(Job)
        .where(
            Job.deleted_at.is_(None),
            or_(job_sim > 0.2, Job.title.icontains(query, autoescape=True)),
        )
        .order_by(job_sim.desc())
        .limit(10),
    )
    jobs = [
        {
            "id": str(j.id),
            "label": j.title,
            "slug": j.slug,
            "type": "job",
            "href": f"/jobs/{j.id}",
        }
        for j in await session.scalars(job_stmt)
    ]
    return {"candidates": candidates, "jobs": jobs}
