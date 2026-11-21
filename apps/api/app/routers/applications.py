import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_roles
from app.core.pagination import Page, PageParams, page_params
from app.models import User
from app.models.enums import CandidateSource, UserRole
from app.schemas.application import (
    AnalysisOut,
    ApplicationFilters,
    ApplicationListItem,
    ApplicationOut,
    StagePatch,
    StageRef,
)
from app.services import analysis as analysis_service
from app.services import applications as applications_service

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])

Session = Annotated[AsyncSession, Depends(get_db)]
StageEditor = Annotated[
    User,
    Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER)),
]


def application_filters(
    job_id: uuid.UUID | None = None,
    stage_id: uuid.UUID | None = None,
    candidate_id: uuid.UUID | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    source: CandidateSource | None = None,
    applied_from: date | None = None,
    applied_to: date | None = None,
    score_min: Annotated[int | None, Query(ge=0, le=100)] = None,
    score_max: Annotated[int | None, Query(ge=0, le=100)] = None,
    skill: Annotated[str | None, Query(max_length=100)] = None,
) -> ApplicationFilters:
    return ApplicationFilters(
        job_id=job_id,
        stage_id=stage_id,
        candidate_id=candidate_id,
        q=q,
        source=source,
        applied_from=applied_from,
        applied_to=applied_to,
        score_min=score_min,
        score_max=score_max,
        skill=skill,
    )


@router.get("/stages", response_model=list[StageRef])
async def list_stages(user: CurrentUser, session: Session) -> list[StageRef]:
    return await applications_service.list_pipeline_stages(session, user)


@router.get("", response_model=Page[ApplicationListItem])
async def list_applications(
    user: CurrentUser,
    session: Session,
    params: Annotated[PageParams, Depends(page_params)],
    filters: Annotated[ApplicationFilters, Depends(application_filters)],
) -> Page[ApplicationListItem]:
    items, total = await applications_service.list_applications(session, user, params, filters)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{application_id}", response_model=ApplicationOut)
async def get_application(
    application_id: uuid.UUID, user: CurrentUser, session: Session
) -> ApplicationOut:
    return await applications_service.get_application(session, user, application_id)


@router.patch("/{application_id}/stage", response_model=ApplicationOut)
async def patch_stage(
    application_id: uuid.UUID, body: StagePatch, user: StageEditor, session: Session
) -> ApplicationOut:
    return await applications_service.move_stage(session, user, application_id, body)


@router.get("/{application_id}/analysis", response_model=AnalysisOut)
async def get_analysis(
    application_id: uuid.UUID, user: CurrentUser, session: Session
) -> AnalysisOut:
    return await analysis_service.get_analysis(session, user, application_id)
