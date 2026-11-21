import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_roles
from app.core.errors import AppError
from app.models import User
from app.models.enums import CandidateSource, UserRole
from app.schemas.application import ManualCandidateCreate, ManualCandidateResult, TimelineEntry
from app.schemas.candidate_actions import (
    CandidatePatch,
    CandidateTagsOut,
    NoteCreate,
    NoteOut,
)
from app.services import analysis as analysis_service
from app.services import applications as applications_service
from app.services import candidate_actions as actions_service

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])

Session = Annotated[AsyncSession, Depends(get_db)]
CandidateEditor = Annotated[
    User,
    Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER)),
]


@router.get("/{candidate_id}/timeline", response_model=list[TimelineEntry])
async def candidate_timeline(
    candidate_id: uuid.UUID, user: CurrentUser, session: Session
) -> list[TimelineEntry]:
    return await applications_service.candidate_timeline(session, user, candidate_id)


@router.get("/{candidate_id}/notes", response_model=list[NoteOut])
async def list_notes(candidate_id: uuid.UUID, user: CurrentUser, session: Session) -> list[NoteOut]:
    return await actions_service.list_notes(session, user, candidate_id)


@router.post("/{candidate_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(
    candidate_id: uuid.UUID, body: NoteCreate, user: CurrentUser, session: Session
) -> NoteOut:
    """CAND-05: add a note; `mentions` is a list of user ids."""
    return await actions_service.create_note(session, user, candidate_id, body)


@router.patch("/{candidate_id}", response_model=CandidateTagsOut)
async def patch_candidate(
    candidate_id: uuid.UUID, body: CandidatePatch, user: CandidateEditor, session: Session
) -> CandidateTagsOut:
    """CAND-05: replace the candidate's tags."""
    return await actions_service.set_candidate_tags(session, user, candidate_id, body.tags)


@router.post("", response_model=ManualCandidateResult, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    user: CandidateEditor,
    session: Session,
    first_name: Annotated[str, Form()],
    last_name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    phone: Annotated[str | None, Form()] = None,
    current_location: Annotated[str | None, Form()] = None,
    current_company: Annotated[str | None, Form()] = None,
    current_title: Annotated[str | None, Form()] = None,
    total_experience_years: Annotated[str | None, Form()] = None,
    notice_period_days: Annotated[int | None, Form()] = None,
    linkedin_url: Annotated[str | None, Form()] = None,
    job_id: Annotated[uuid.UUID | None, Form()] = None,
    source: Annotated[str, Form()] = CandidateSource.MANUAL.value,
    tags: Annotated[str | None, Form()] = None,
    cv: Annotated[UploadFile | None, File()] = None,
) -> ManualCandidateResult:
    """CAND-10: manual candidate create with optional CV and job link."""
    tag_list: list[str] = []
    if tags:
        try:
            parsed = json.loads(tags)
            if isinstance(parsed, list):
                tag_list = [str(t) for t in parsed]
            else:
                tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        except json.JSONDecodeError:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    years = None
    if total_experience_years not in (None, ""):
        from decimal import Decimal, InvalidOperation

        try:
            years = Decimal(total_experience_years)
        except InvalidOperation as exc:
            raise AppError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_error",
                "Invalid total_experience_years",
            ) from exc

    try:
        source_enum = CandidateSource(source)
    except ValueError:
        source_enum = CandidateSource.MANUAL

    body = ManualCandidateCreate(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        current_location=current_location,
        current_company=current_company,
        current_title=current_title,
        total_experience_years=years,
        notice_period_days=notice_period_days,
        linkedin_url=linkedin_url,
        job_id=job_id,
        source=source_enum,
        tags=tag_list,
    )
    cv_bytes = await cv.read() if cv is not None else None
    cv_name = cv.filename if cv is not None else None
    return await analysis_service.create_manual_candidate(session, user, body, cv_bytes, cv_name)
