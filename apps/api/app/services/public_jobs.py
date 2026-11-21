import uuid

from fastapi import status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.pagination import PageParams, apply_sort, paginate
from app.models import Department, Job, JobRequirement, Location
from app.schemas.job import NamedRef, PublicJobFilters, PublicJobListItem, PublicJobOut
from app.services.jobs import named_ref, public_job_conditions


def _list_item(job: Job, department: str | None, location: str | None) -> PublicJobListItem:
    return PublicJobListItem(
        slug=job.slug,
        title=job.title,
        department=named_ref(job.department_id, department),
        location=named_ref(job.location_id, location),
        work_mode=job.work_mode,
        employment_type=job.employment_type,
        level=job.level,
        published_at=job.published_at,
        closes_at=job.closes_at,
    )


def _base_query() -> Select[tuple[Job, str, str]]:
    return (
        select(Job, Department.name, Location.name)
        .outerjoin(Department, Department.id == Job.department_id)
        .outerjoin(Location, Location.id == Job.location_id)
        .where(*public_job_conditions())
    )


async def list_public_jobs(
    session: AsyncSession,
    params: PageParams,
    *,
    q: str | None = None,
    department_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
) -> tuple[list[PublicJobListItem], int]:
    stmt = _base_query()
    if q and q.strip():
        stmt = stmt.where(Job.title.icontains(q.strip(), autoescape=True))
    if department_id is not None:
        stmt = stmt.where(Job.department_id == department_id)
    if location_id is not None:
        stmt = stmt.where(Job.location_id == location_id)
    sortable = {"title": Job.title, "published_at": Job.published_at, "closes_at": Job.closes_at}
    stmt = apply_sort(stmt, params.sort, sortable, default="-published_at")
    rows, total = await paginate(session, stmt, params)
    return [_list_item(*row) for row in rows], total


async def get_public_filters(session: AsyncSession) -> PublicJobFilters:
    """Departments and locations that currently have at least one public job."""
    open_jobs = select(Job.department_id, Job.location_id).where(*public_job_conditions())
    departments = await session.execute(
        select(Department.id, Department.name)
        .where(Department.id.in_(open_jobs.with_only_columns(Job.department_id)))
        .order_by(Department.name)
    )
    locations = await session.execute(
        select(Location.id, Location.name)
        .where(Location.id.in_(open_jobs.with_only_columns(Job.location_id)))
        .order_by(Location.name)
    )
    return PublicJobFilters(
        departments=[NamedRef(id=i, name=n) for i, n in departments],
        locations=[NamedRef(id=i, name=n) for i, n in locations],
    )


async def get_public_job(session: AsyncSession, slug: str) -> PublicJobOut:
    row = (await session.execute(_base_query().where(Job.slug == slug))).first()
    if row is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Job not found")
    job, department, location = row
    requirement = await session.scalar(
        select(JobRequirement).where(JobRequirement.job_id == job.id)
    )
    return PublicJobOut(
        **_list_item(job, department, location).model_dump(),
        description=job.description,
        responsibilities=job.responsibilities,
        qualifications=job.qualifications,
        openings=job.openings,
        required_skills=[s["name"] for s in requirement.required_skills] if requirement else [],
        preferred_skills=[s["name"] for s in requirement.preferred_skills] if requirement else [],
        min_experience=requirement.min_experience if requirement else None,
        education_level=requirement.education_level if requirement else None,
    )
