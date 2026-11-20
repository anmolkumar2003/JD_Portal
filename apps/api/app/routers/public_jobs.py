import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.pagination import Page, PageParams, page_params
from app.core.redis import get_redis
from app.schemas.application import ApplyForm, ApplyResult
from app.schemas.job import PublicJobFilters, PublicJobListItem, PublicJobOut
from app.services import applications as applications_service
from app.services import public_jobs as public_jobs_service
from app.services.cv_validation import MAX_CV_BYTES

router = APIRouter(prefix="/api/v1/public/jobs", tags=["public"])

Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=Page[PublicJobListItem])
async def list_public_jobs(
    session: Session,
    params: Annotated[PageParams, Depends(page_params)],
    q: Annotated[str | None, Query(max_length=200)] = None,
    department_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
) -> Page[PublicJobListItem]:
    items, total = await public_jobs_service.list_public_jobs(
        session, params, q=q, department_id=department_id, location_id=location_id
    )
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/filters", response_model=PublicJobFilters)
async def get_public_job_filters(session: Session) -> PublicJobFilters:
    return await public_jobs_service.get_public_filters(session)


@router.get("/{slug}", response_model=PublicJobOut)
async def get_public_job(slug: str, session: Session) -> PublicJobOut:
    return await public_jobs_service.get_public_job(session, slug)


@router.post("/{slug}/apply", response_model=ApplyResult, status_code=status.HTTP_201_CREATED)
async def apply_to_job(  # noqa: PLR0913, PLR0917 - FastAPI injects each part of the request
    slug: str,
    request: Request,
    form: Annotated[ApplyForm, Form()],
    cv: Annotated[UploadFile, File(description="PDF or DOCX, max 5 MB")],
    session: Session,
    redis: Annotated[Redis, Depends(get_redis)],
) -> ApplyResult:
    # Read one byte past the limit so oversized files are rejected without buffering them fully.
    data = await cv.read(MAX_CV_BYTES + 1)
    return await applications_service.apply(
        session,
        redis,
        slug=slug,
        form=form,
        cv_bytes=data,
        cv_file_name=cv.filename,
        client_ip=request.client.host if request.client else "unknown",
    )
