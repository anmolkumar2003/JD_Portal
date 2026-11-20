import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_roles
from app.core.pagination import Page, PageParams, page_params
from app.models import User
from app.models.enums import JobStatus, UserRole
from app.schemas.application import BoardOut
from app.schemas.job import (
    JobCreate,
    JobFilters,
    JobListItem,
    JobOut,
    JobUpdate,
    RequirementsIn,
    TeamIn,
)
from app.services import applications as applications_service
from app.services import jobs as jobs_service

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

Session = Annotated[AsyncSession, Depends(get_db)]
JobEditor = Annotated[
    User,
    Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER)),
]


def job_filters(
    status_filter: Annotated[JobStatus | None, Query(alias="status")] = None,
    department_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> JobFilters:
    return JobFilters(
        status=status_filter, department_id=department_id, location_id=location_id, q=q
    )


@router.get("", response_model=Page[JobListItem])
async def list_jobs(
    user: CurrentUser,
    session: Session,
    params: Annotated[PageParams, Depends(page_params)],
    filters: Annotated[JobFilters, Depends(job_filters)],
) -> Page[JobListItem]:
    items, total = await jobs_service.list_jobs(session, user, params, filters)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
async def create_job(body: JobCreate, user: JobEditor, session: Session) -> JobOut:
    return await jobs_service.create_job(session, user, body)


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: uuid.UUID, user: CurrentUser, session: Session) -> JobOut:
    return await jobs_service.get_job(session, user, job_id)


@router.get("/{job_id}/board", response_model=BoardOut)
async def get_job_board(job_id: uuid.UUID, user: CurrentUser, session: Session) -> BoardOut:
    return await applications_service.get_board(session, user, job_id)


@router.patch("/{job_id}", response_model=JobOut)
async def update_job(
    job_id: uuid.UUID, body: JobUpdate, user: JobEditor, session: Session
) -> JobOut:
    return await jobs_service.update_job(session, user, job_id, body)


@router.post("/{job_id}/publish", response_model=JobOut)
async def publish_job(job_id: uuid.UUID, user: JobEditor, session: Session) -> JobOut:
    return await jobs_service.publish_job(session, user, job_id)


@router.post("/{job_id}/close", response_model=JobOut)
async def close_job(job_id: uuid.UUID, user: JobEditor, session: Session) -> JobOut:
    return await jobs_service.close_job(session, user, job_id)


@router.put("/{job_id}/requirements", response_model=JobOut)
async def replace_requirements(
    job_id: uuid.UUID, body: RequirementsIn, user: JobEditor, session: Session
) -> JobOut:
    return await jobs_service.replace_requirements(session, user, job_id, body)


@router.put("/{job_id}/team", response_model=JobOut)
async def replace_team(
    job_id: uuid.UUID, body: TeamIn, user: JobEditor, session: Session
) -> JobOut:
    return await jobs_service.replace_team(session, user, job_id, body)
