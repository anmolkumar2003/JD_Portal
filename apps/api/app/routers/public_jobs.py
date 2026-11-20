import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.pagination import Page, PageParams, page_params
from app.schemas.job import PublicJobListItem, PublicJobOut
from app.services import public_jobs as public_jobs_service

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


@router.get("/{slug}", response_model=PublicJobOut)
async def get_public_job(slug: str, session: Session) -> PublicJobOut:
    return await public_jobs_service.get_public_job(session, slug)
