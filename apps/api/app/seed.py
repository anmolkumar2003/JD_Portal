"""Seed local demo data. Safe to re-run: rows are matched by natural key and reused.

Run with `make seed` (or `python -m app.seed` inside the API container).
Demo credentials are for local development only and are documented in the README.
"""

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.models import (
    Department,
    Job,
    JobRequirement,
    JobTeam,
    Location,
    Organization,
    PipelineStage,
    User,
)
from app.models.base import Base
from app.models.enums import EmploymentType, JobStatus, StageType, TeamRole, UserRole, WorkMode

logger = logging.getLogger("app.seed")

M = TypeVar("M", bound=Base)

DEMO_PASSWORD = "Demo@2026!"  # noqa: S105 - local demo only, documented in README
ORG_NAME = "Acme Corp"
EMAIL_DOMAIN = "acme.example.com"

DEMO_USERS: list[tuple[str, str, UserRole]] = [
    ("superadmin", "Sara Super", UserRole.SUPER_ADMIN),
    ("hradmin", "Harish Admin", UserRole.HR_ADMIN),
    ("recruiter", "Riya Recruiter", UserRole.RECRUITER),
    ("manager", "Manoj Manager", UserRole.HIRING_MANAGER),
    ("interviewer", "Isha Interviewer", UserRole.INTERVIEWER),
]

DEFAULT_STAGES: list[tuple[str, StageType]] = [
    ("Applied", StageType.APPLIED),
    ("Screening", StageType.SCREENING),
    ("Interview", StageType.INTERVIEW),
    ("Offer", StageType.OFFER),
    ("Hired", StageType.HIRED),
    ("Rejected", StageType.REJECTED),
]


def _skills(*items: tuple[str, float]) -> list[dict[str, Any]]:
    return [{"name": name, "weight": weight} for name, weight in items]


async def _get_or_create(
    session: AsyncSession, model: type[M], lookup: dict[str, Any], **values: Any
) -> M:
    instance = await session.scalar(select(model).filter_by(**lookup))
    if instance is None:
        instance = model(**lookup, **values)
        session.add(instance)
        await session.flush()
    return instance


async def seed(session: AsyncSession) -> None:
    org = await _get_or_create(
        session, Organization, {"name": ORG_NAME}, domain=EMAIL_DOMAIN, settings={}
    )

    password_hash = hash_password(DEMO_PASSWORD)
    users: dict[UserRole, User] = {}
    for handle, full_name, role in DEMO_USERS:
        user = await _get_or_create(
            session,
            User,
            {"email": f"{handle}@{EMAIL_DOMAIN}"},
            org_id=org.id,
            full_name=full_name,
            role=role,
            password_hash=password_hash,
        )
        # Re-seeding restores the documented demo state, including after a lockout test.
        user.role = role
        user.is_active = True
        user.password_hash = password_hash
        user.failed_login_attempts = 0
        user.locked_until = None
        users[role] = user

    for order, (name, stage_type) in enumerate(DEFAULT_STAGES, start=1):
        await _get_or_create(
            session,
            PipelineStage,
            {"org_id": org.id, "name": name},
            order=order,
            type=stage_type,
            is_default=True,
        )

    manager = users[UserRole.HIRING_MANAGER]
    engineering = await _get_or_create(
        session, Department, {"org_id": org.id, "name": "Engineering"}, head_user_id=manager.id
    )
    people = await _get_or_create(
        session, Department, {"org_id": org.id, "name": "People Operations"}
    )
    bengaluru = await _get_or_create(
        session,
        Location,
        {"org_id": org.id, "name": "Bengaluru HQ"},
        city="Bengaluru",
        country="India",
    )
    remote = await _get_or_create(
        session, Location, {"org_id": org.id, "name": "Remote (India)"}, country="India"
    )

    now = datetime.now(UTC)
    recruiter = users[UserRole.RECRUITER]
    interviewer = users[UserRole.INTERVIEWER]
    jobs: list[dict[str, Any]] = [
        {
            "slug": "senior-backend-engineer",
            "title": "Senior Backend Engineer",
            "department_id": engineering.id,
            "location_id": bengaluru.id,
            "work_mode": WorkMode.HYBRID,
            "employment_type": EmploymentType.FULL_TIME,
            "level": "Senior",
            "description": "Build and scale the APIs behind our recruitment platform.",
            "responsibilities": "Design services, own reliability, mentor engineers.",
            "qualifications": "5+ years building production backend systems.",
            "salary_min": Decimal("2500000"),
            "salary_max": Decimal("4000000"),
            "openings": 2,
            "status": JobStatus.OPEN,
            "published_at": now,
            "hiring_manager_id": manager.id,
            "team": [
                (recruiter, TeamRole.RECRUITER),
                (manager, TeamRole.MANAGER),
                (interviewer, TeamRole.INTERVIEWER),
            ],
            "requirements": {
                "required_skills": _skills(
                    ("Python", 1.0), ("FastAPI", 0.8), ("PostgreSQL", 0.8), ("Docker", 0.6)
                ),
                "preferred_skills": _skills(("Kubernetes", 0.5), ("Celery", 0.4), ("AWS", 0.4)),
                "min_experience": Decimal("5"),
                "max_experience": Decimal("10"),
                "education_level": "Bachelor's",
                "certifications": [],
            },
        },
        {
            "slug": "frontend-engineer",
            "title": "Frontend Engineer",
            "department_id": engineering.id,
            "location_id": remote.id,
            "work_mode": WorkMode.REMOTE,
            "employment_type": EmploymentType.FULL_TIME,
            "level": "Mid",
            "description": "Craft fast, accessible interfaces for recruiters and candidates.",
            "responsibilities": "Build React features, own UI quality and accessibility.",
            "qualifications": "3+ years with React and TypeScript.",
            "salary_min": Decimal("1500000"),
            "salary_max": Decimal("2800000"),
            "openings": 1,
            "status": JobStatus.OPEN,
            "published_at": now,
            "hiring_manager_id": manager.id,
            "team": [(recruiter, TeamRole.RECRUITER), (manager, TeamRole.MANAGER)],
            "requirements": {
                "required_skills": _skills(
                    ("React", 1.0), ("TypeScript", 1.0), ("Next.js", 0.7), ("CSS", 0.5)
                ),
                "preferred_skills": _skills(("Tailwind CSS", 0.5), ("Playwright", 0.4)),
                "min_experience": Decimal("3"),
                "max_experience": Decimal("7"),
                "education_level": None,
                "certifications": [],
            },
        },
        {
            "slug": "hr-business-partner",
            "title": "HR Business Partner",
            "department_id": people.id,
            "location_id": bengaluru.id,
            "work_mode": WorkMode.ONSITE,
            "employment_type": EmploymentType.FULL_TIME,
            "level": "Senior",
            "description": "Partner with leaders on talent, performance and culture.",
            "responsibilities": "Advise managers, run talent reviews, drive engagement.",
            "qualifications": "6+ years in HR business partnering.",
            "salary_min": Decimal("1800000"),
            "salary_max": Decimal("3000000"),
            "openings": 1,
            "status": JobStatus.DRAFT,
            "published_at": None,
            "hiring_manager_id": None,
            "team": [(recruiter, TeamRole.RECRUITER)],
            "requirements": {
                "required_skills": _skills(
                    ("Employee Relations", 1.0), ("Talent Management", 0.8), ("HR Analytics", 0.6)
                ),
                "preferred_skills": _skills(("SHRM-CP", 0.5), ("Workday", 0.4)),
                "min_experience": Decimal("6"),
                "max_experience": None,
                "education_level": "Master's",
                "certifications": ["SHRM-CP"],
            },
        },
    ]

    for spec in jobs:
        team = spec.pop("team")
        requirements = spec.pop("requirements")
        slug = spec.pop("slug")
        job = await _get_or_create(
            session,
            Job,
            {"slug": slug},
            org_id=org.id,
            created_by=recruiter.id,
            salary_currency="INR",
            **spec,
        )
        await _get_or_create(session, JobRequirement, {"job_id": job.id}, **requirements)
        for member, team_role in team:
            await _get_or_create(
                session, JobTeam, {"job_id": job.id, "user_id": member.id, "team_role": team_role}
            )

    await session.commit()


async def main() -> None:
    configure_logging(get_settings().log_level)
    async with SessionLocal() as session:
        await seed(session)
    await engine.dispose()
    logger.info(
        "seed complete",
        extra={"org": ORG_NAME, "users": len(DEMO_USERS), "stages": len(DEFAULT_STAGES), "jobs": 3},
    )


if __name__ == "__main__":
    asyncio.run(main())
