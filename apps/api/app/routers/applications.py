import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_roles
from app.core.pagination import Page, PageParams, page_params
from app.models import User
from app.models.enums import CandidateSource, UserRole
from app.schemas.application import (
    ApplicationDetail,
    ApplicationFilters,
    ApplicationListItem,
    StageChangeIn,
)
from app.services import applications as applications_service

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])

Session = Annotated[AsyncSession, Depends(get_db)]
StageEditor = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.HR_ADMIN,
            UserRole.RECRUITER,
            UserRole.HIRING_MANAGER,
        )
    ),
]


def application_filters(  # noqa: PLR0913, PLR0917 - query deps mirror the filter fields
    job_id: uuid.UUID | None = None,
    stage_id: uuid.UUID | None = None,
    candidate_id: uuid.UUID | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    source: CandidateSource | None = None,
    applied_from: datetime | None = None,
    applied_to: datetime | None = None,
) -> ApplicationFilters:
    return ApplicationFilters(
        job_id=job_id,
        stage_id=stage_id,
        candidate_id=candidate_id,
        q=q,
        source=source,
        applied_from=applied_from,
        applied_to=applied_to,
    )


@router.get("", response_model=Page[ApplicationListItem])
async def list_applications(
    user: CurrentUser,
    session: Session,
    params: Annotated[PageParams, Depends(page_params)],
    filters: Annotated[ApplicationFilters, Depends(application_filters)],
) -> Page[ApplicationListItem]:
    items, total = await applications_service.list_applications(session, user, params, filters)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{application_id}", response_model=ApplicationDetail)
async def get_application(
    application_id: uuid.UUID, user: CurrentUser, session: Session
) -> ApplicationDetail:
    return await applications_service.get_application(session, user, application_id)


@router.patch("/{application_id}/stage", response_model=ApplicationDetail)
async def change_stage(
    application_id: uuid.UUID,
    body: StageChangeIn,
    user: StageEditor,
    session: Session,
) -> ApplicationDetail:
    return await applications_service.change_stage(session, user, application_id, body)
