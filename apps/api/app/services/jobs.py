import re
import unicodedata
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import ColumnElement, Label, Select, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import scope_jobs_query
from app.core.errors import AppError
from app.core.pagination import PageParams, apply_sort, paginate
from app.models import (
    ActivityLog,
    Application,
    Department,
    Job,
    JobRequirement,
    JobTeam,
    Location,
    User,
)
from app.models.enums import JobStatus, TeamRole, UserRole
from app.schemas.job import (
    JobCreate,
    JobFilters,
    JobListItem,
    JobOut,
    JobUpdate,
    NamedRef,
    RequirementsIn,
    RequirementsOut,
    TeamIn,
    TeamMemberOut,
)

_NON_SLUG = re.compile(r"[^a-z0-9]+")
# target status -> (statuses it may be reached from, activity-log action)
TRANSITIONS: dict[JobStatus, tuple[frozenset[JobStatus], str]] = {
    JobStatus.OPEN: (frozenset({JobStatus.DRAFT, JobStatus.ON_HOLD}), "job.published"),
    JobStatus.CLOSED: (
        frozenset({JobStatus.DRAFT, JobStatus.OPEN, JobStatus.ON_HOLD}),
        "job.closed",
    ),
}


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = _NON_SLUG.sub("-", ascii_text.lower()).strip("-")[:200].rstrip("-")
    return slug or "job"


async def _unique_slug(session: AsyncSession, title: str) -> str:
    """Slugs are global (careers URLs) and include soft-deleted jobs, so links never collide."""
    base = slugify(title)
    taken = set(
        await session.scalars(
            select(Job.slug).where(or_(Job.slug == base, Job.slug.like(f"{base}-%")))
        )
    )
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def _not_found() -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "not_found", "Job not found")


def named_ref(id_: uuid.UUID | None, name: str | None) -> NamedRef | None:
    return NamedRef(id=id_, name=name) if id_ is not None and name is not None else None


def _applicants_count() -> Label[int]:
    return (
        select(func.count(Application.id))
        .where(Application.job_id == Job.id)
        .correlate(Job)
        .scalar_subquery()
        .label("applicants_count")
    )


def _job_rows_query(applicants: Label[int]) -> Select[tuple[Job, str, str, int]]:
    # Department and location names are None at runtime when the outer join finds no row.
    return (
        select(Job, Department.name, Location.name, applicants)
        .outerjoin(Department, Department.id == Job.department_id)
        .outerjoin(Location, Location.id == Job.location_id)
    )


def _list_item(job: Job, department: str | None, location: str | None, count: int) -> JobListItem:
    return JobListItem(
        id=job.id,
        title=job.title,
        slug=job.slug,
        status=job.status,
        department=named_ref(job.department_id, department),
        location=named_ref(job.location_id, location),
        work_mode=job.work_mode,
        employment_type=job.employment_type,
        openings=job.openings,
        applicants_count=count,
        published_at=job.published_at,
        closes_at=job.closes_at,
        created_at=job.created_at,
    )


# --- Reads ------------------------------------------------------------------------------------


async def list_jobs(
    session: AsyncSession, user: User, params: PageParams, filters: JobFilters
) -> tuple[list[JobListItem], int]:
    applicants = _applicants_count()
    stmt = scope_jobs_query(user, _job_rows_query(applicants))
    if filters.status is not None:
        stmt = stmt.where(Job.status == filters.status)
    if filters.department_id is not None:
        stmt = stmt.where(Job.department_id == filters.department_id)
    if filters.location_id is not None:
        stmt = stmt.where(Job.location_id == filters.location_id)
    if filters.q and filters.q.strip():
        stmt = stmt.where(Job.title.icontains(filters.q.strip(), autoescape=True))

    sortable: dict[str, Any] = {
        "title": Job.title,
        "status": Job.status,
        "created_at": Job.created_at,
        "published_at": Job.published_at,
        "closes_at": Job.closes_at,
        "applicants_count": applicants,
    }
    stmt = apply_sort(stmt, params.sort, sortable, default="-created_at")
    rows, total = await paginate(session, stmt, params)
    return [_list_item(*row) for row in rows], total


async def _get_scoped_job(session: AsyncSession, user: User, job_id: uuid.UUID) -> Job:
    job = await session.scalar(scope_jobs_query(user, select(Job).where(Job.id == job_id)))
    if job is None:
        raise _not_found()
    return job


async def _build_job_out(session: AsyncSession, job: Job) -> JobOut:
    applicants = _applicants_count()
    row = (await session.execute(_job_rows_query(applicants).where(Job.id == job.id))).one()
    _, department, location, count = row

    requirement = await session.scalar(
        select(JobRequirement).where(JobRequirement.job_id == job.id)
    )
    team_rows = await session.execute(
        select(JobTeam.team_role, User)
        .join(User, User.id == JobTeam.user_id)
        .where(JobTeam.job_id == job.id)
        .order_by(JobTeam.team_role, User.full_name)
    )
    team = [
        TeamMemberOut(
            user_id=member.id,
            full_name=member.full_name,
            email=member.email,
            role=member.role,
            team_role=team_role,
        )
        for team_role, member in team_rows
    ]
    manager = await session.get(User, job.hiring_manager_id) if job.hiring_manager_id else None

    return JobOut(
        **_list_item(job, department, location, count).model_dump(),
        level=job.level,
        description=job.description,
        responsibilities=job.responsibilities,
        qualifications=job.qualifications,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
        updated_at=job.updated_at,
        hiring_manager=named_ref(manager.id, manager.full_name) if manager else None,
        requirements=RequirementsOut.model_validate(requirement) if requirement else None,
        team=team,
    )


async def get_job(session: AsyncSession, user: User, job_id: uuid.UUID) -> JobOut:
    return await _build_job_out(session, await _get_scoped_job(session, user, job_id))


# --- Writes -----------------------------------------------------------------------------------


async def _check_refs(
    session: AsyncSession,
    user: User,
    department_id: uuid.UUID | None,
    location_id: uuid.UUID | None,
) -> None:
    if department_id is not None:
        department = await session.get(Department, department_id)
        if department is None or department.org_id != user.org_id:
            raise AppError(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_reference", "Unknown department"
            )
    if location_id is not None:
        location = await session.get(Location, location_id)
        if location is None or location.org_id != user.org_id:
            raise AppError(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_reference", "Unknown location"
            )


def _apply_requirements(requirement: JobRequirement, data: RequirementsIn) -> None:
    requirement.required_skills = [s.model_dump() for s in data.required_skills]
    requirement.preferred_skills = [s.model_dump() for s in data.preferred_skills]
    requirement.min_experience = data.min_experience
    requirement.max_experience = data.max_experience
    requirement.education_level = data.education_level or None


async def create_job(session: AsyncSession, user: User, data: JobCreate) -> JobOut:
    await _check_refs(session, user, data.department_id, data.location_id)
    job = Job(
        org_id=user.org_id,
        slug=await _unique_slug(session, data.title),
        created_by=user.id,
        status=JobStatus.DRAFT,
        **data.model_dump(exclude={"requirements"}),
    )
    session.add(job)
    await session.flush()

    requirement = JobRequirement(job_id=job.id, certifications=[])
    _apply_requirements(requirement, data.requirements or RequirementsIn())
    session.add(requirement)
    if user.role == UserRole.RECRUITER:
        session.add(JobTeam(job_id=job.id, user_id=user.id, team_role=TeamRole.RECRUITER))
    await session.commit()
    await session.refresh(job)
    return await _build_job_out(session, job)


async def update_job(
    session: AsyncSession, user: User, job_id: uuid.UUID, data: JobUpdate
) -> JobOut:
    job = await _get_scoped_job(session, user, job_id)
    changes = data.model_dump(exclude_unset=True)
    for required in ("title", "work_mode", "employment_type", "openings"):
        if required in changes and changes[required] is None:
            raise AppError(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "validation_error", f"{required} is required"
            )
    await _check_refs(session, user, changes.get("department_id"), changes.get("location_id"))

    for field, value in changes.items():
        setattr(job, field, value)
    if job.description is None:
        job.description = ""
    if (
        job.salary_min is not None
        and job.salary_max is not None
        and job.salary_min > job.salary_max
    ):
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "validation_error",
            "Salary minimum must not exceed the maximum",
        )
    await session.commit()
    await session.refresh(job)
    return await _build_job_out(session, job)


async def _transition(session: AsyncSession, user: User, job: Job, target: JobStatus) -> JobOut:
    allowed_from, action = TRANSITIONS[target]
    if job.status not in allowed_from:
        raise AppError(
            status.HTTP_409_CONFLICT,
            "invalid_status_transition",
            f"A {job.status.value} job cannot be moved to {target.value}",
        )
    previous = job.status
    job.status = target
    if target == JobStatus.OPEN:
        job.published_at = datetime.now(UTC)
    session.add(
        ActivityLog(
            actor_id=user.id,
            action=action,
            meta={"job_id": str(job.id), "from": previous.value, "to": target.value},
        )
    )
    await session.commit()
    await session.refresh(job)
    return await _build_job_out(session, job)


async def publish_job(session: AsyncSession, user: User, job_id: uuid.UUID) -> JobOut:
    job = await _get_scoped_job(session, user, job_id)
    problems: list[str] = []
    if not job.description.strip():
        problems.append("Add a job description")
    if job.closes_at is not None and job.closes_at <= datetime.now(UTC):
        problems.append("The closing date is in the past")
    if problems:
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "job_incomplete",
            "The job is not ready to publish",
            problems,
        )
    return await _transition(session, user, job, JobStatus.OPEN)


async def close_job(session: AsyncSession, user: User, job_id: uuid.UUID) -> JobOut:
    job = await _get_scoped_job(session, user, job_id)
    return await _transition(session, user, job, JobStatus.CLOSED)


async def replace_requirements(
    session: AsyncSession, user: User, job_id: uuid.UUID, data: RequirementsIn
) -> JobOut:
    job = await _get_scoped_job(session, user, job_id)
    requirement = await session.scalar(
        select(JobRequirement).where(JobRequirement.job_id == job.id)
    )
    if requirement is None:
        requirement = JobRequirement(job_id=job.id, certifications=[])
        session.add(requirement)
    _apply_requirements(requirement, data)
    await session.commit()
    return await _build_job_out(session, job)


async def replace_team(
    session: AsyncSession, user: User, job_id: uuid.UUID, data: TeamIn
) -> JobOut:
    """Replace the job's team (JOB-06). The hiring manager is also stored as a manager member."""
    job = await _get_scoped_job(session, user, job_id)
    members = {(m.user_id, m.team_role) for m in data.members}
    if data.hiring_manager_id is not None:
        members.add((data.hiring_manager_id, TeamRole.MANAGER))

    user_ids = {user_id for user_id, _ in members}
    found: Sequence[User] = (
        await session.scalars(
            select(User).where(
                User.id.in_(user_ids), User.org_id == user.org_id, User.is_active.is_(True)
            )
        )
    ).all()
    users = {u.id: u for u in found}
    if missing := user_ids - users.keys():
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "invalid_reference",
            "Unknown or inactive users",
            [str(m) for m in missing],
        )
    manager_id = data.hiring_manager_id
    if manager_id is not None and users[manager_id].role != UserRole.HIRING_MANAGER:
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "invalid_reference",
            "The hiring manager must have the hiring_manager role",
        )

    await session.execute(delete(JobTeam).where(JobTeam.job_id == job.id))
    session.add_all(
        JobTeam(job_id=job.id, user_id=user_id, team_role=team_role)
        for user_id, team_role in members
    )
    job.hiring_manager_id = data.hiring_manager_id
    await session.commit()
    await session.refresh(job)
    return await _build_job_out(session, job)


def public_job_conditions() -> list[ColumnElement[bool]]:
    """A job is on the careers site only while open, published and not past its closing date."""
    return [
        Job.status == JobStatus.OPEN,
        Job.published_at.is_not(None),
        Job.deleted_at.is_(None),
        or_(Job.closes_at.is_(None), Job.closes_at > func.now()),
    ]
