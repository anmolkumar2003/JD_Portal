import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_roles
from app.core.pagination import Page, PageParams, page_params
from app.models import User
from app.models.enums import ApplicationStatus, CandidateSource, SalaryUnit, UserRole
from app.schemas.application import (
    AnalysisOut,
    ApplicationFilters,
    ApplicationListItem,
    ApplicationOut,
    StagePatch,
    StageRef,
)
from app.schemas.candidate_actions import (
    BulkActionRequest,
    BulkActionResult,
    ShortlistOut,
    ShortlistPatch,
)
from app.services import analysis as analysis_service
from app.services import applications as applications_service
from app.services import candidate_actions as actions_service

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
    department_id: uuid.UUID | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    source: CandidateSource | None = None,
    applied_from: date | None = None,
    applied_to: date | None = None,
    score_min: Annotated[int | None, Query(ge=0, le=100)] = None,
    score_max: Annotated[int | None, Query(ge=0, le=100)] = None,
    skill: Annotated[str | None, Query(max_length=100)] = None,
    skills: Annotated[list[str] | None, Query()] = None,
    skills_mode: Annotated[str, Query(pattern="^(any|all)$")] = "any",
    tag: Annotated[str | None, Query(max_length=50)] = None,
    is_shortlisted: bool | None = None,
    location: Annotated[str | None, Query(max_length=200)] = None,
    experience_min: Annotated[float | None, Query(ge=0, le=60)] = None,
    experience_max: Annotated[float | None, Query(ge=0, le=60)] = None,
    notice_min_days: Annotated[int | None, Query(ge=0, le=730)] = None,
    notice_max_days: Annotated[int | None, Query(ge=0, le=730)] = None,
    expected_ctc_min: Decimal | None = None,
    expected_ctc_max: Decimal | None = None,
    expected_ctc_currency: Annotated[str | None, Query(min_length=3, max_length=3)] = None,
    expected_ctc_unit: SalaryUnit | None = None,
    ats_score_min: Annotated[int | None, Query(ge=0, le=100)] = None,
    ats_score_max: Annotated[int | None, Query(ge=0, le=100)] = None,
    rating_min: Annotated[float | None, Query(ge=1, le=5)] = None,
    rating_max: Annotated[float | None, Query(ge=1, le=5)] = None,
    status: ApplicationStatus | None = None,
) -> ApplicationFilters:
    skill_list = [s.strip() for s in (skills or []) if s and s.strip()]
    return ApplicationFilters(
        job_id=job_id,
        stage_id=stage_id,
        candidate_id=candidate_id,
        department_id=department_id,
        q=q,
        source=source,
        applied_from=applied_from,
        applied_to=applied_to,
        score_min=score_min,
        score_max=score_max,
        skill=skill,
        skills=skill_list,
        skills_mode=skills_mode,
        tag=tag,
        is_shortlisted=is_shortlisted,
        location=location,
        experience_min=experience_min,
        experience_max=experience_max,
        notice_min_days=notice_min_days,
        notice_max_days=notice_max_days,
        expected_ctc_min=expected_ctc_min,
        expected_ctc_max=expected_ctc_max,
        expected_ctc_currency=expected_ctc_currency.upper() if expected_ctc_currency else None,
        expected_ctc_unit=expected_ctc_unit,
        ats_score_min=ats_score_min,
        ats_score_max=ats_score_max,
        rating_min=rating_min,
        rating_max=rating_max,
        status=status,
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


@router.post("/bulk-action", response_model=BulkActionResult)
async def bulk_action(
    body: BulkActionRequest, user: StageEditor, session: Session
) -> BulkActionResult:
    """CAND-06: move stage, reject with reason, or tag many applications at once."""
    return await actions_service.bulk_action(session, user, body)


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


@router.post("/{application_id}/shortlist", response_model=ShortlistOut)
async def shortlist(
    application_id: uuid.UUID,
    user: StageEditor,
    session: Session,
    body: ShortlistPatch | None = None,
) -> ShortlistOut:
    """CAND-05: star/shortlist an application. Omit the body to toggle."""
    return await actions_service.set_shortlist(
        session, user, application_id, body.shortlisted if body else None
    )
