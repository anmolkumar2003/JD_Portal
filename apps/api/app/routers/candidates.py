import json
import uuid
from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import AdminUser, CurrentUser, require_roles
from app.core.errors import AppError, validation_app_error
from app.core.redis import get_redis
from app.models import User
from app.models.enums import CandidateSource, DocumentType, SalaryUnit, UserRole
from app.schemas.application import (
    CvParseOut,
    DocumentOut,
    DuplicateCheckOut,
    ManualCandidateCreate,
    ManualCandidateResult,
    TimelineEntry,
)
from app.schemas.candidate_actions import CandidateOut, CandidatePatch, NoteCreate, NoteOut
from app.schemas.candidate_delete import (
    BulkCandidateDeleteOut,
    BulkCandidateDeleteRequest,
    CandidateDeleteOut,
)
from app.schemas.candidate_drafts import (
    DraftCommitIn,
    DraftCommitOut,
    DraftDeleteOut,
    DraftFileUploadOut,
    DraftOut,
)
from app.schemas.salary import SalaryIn
from app.services import analysis as analysis_service
from app.services import applications as applications_service
from app.services import candidate_actions as actions_service
from app.services import candidate_delete as delete_service
from app.services import candidate_drafts as drafts_service
from app.services import documents as documents_service
from app.services.cv_validation import MAX_CV_BYTES

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])

Session = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]
CandidateEditor = Annotated[
    User,
    Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER)),
]


def _salary_from_form(
    amount: str | None,
    currency: str | None,
    unit: str | None,
    negotiable: bool | None,
) -> SalaryIn | None:
    if amount is None and currency is None and unit is None and negotiable is None:
        return None
    parsed_amount: Decimal | None = None
    if amount not in (None, ""):
        try:
            parsed_amount = Decimal(str(amount))
        except InvalidOperation as exc:
            raise AppError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_error",
                "Invalid salary amount",
            ) from exc
    try:
        salary_unit = SalaryUnit(unit) if unit else SalaryUnit.PA
    except ValueError as exc:
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_error", "Invalid salary unit"
        ) from exc
    currency_code = (currency or "INR").upper()
    return SalaryIn(
        amount=parsed_amount,
        currency=currency_code,
        unit=salary_unit,
        negotiable=bool(negotiable),
    )


@router.post("/parse-cv", response_model=CvParseOut)
async def parse_cv(
    user: CandidateEditor,
    cv: Annotated[UploadFile, File()],
) -> CvParseOut:
    """Extract autofill fields from a CV. Nothing is stored (use drafts to keep the file)."""
    data = await cv.read(MAX_CV_BYTES + 1)
    return await analysis_service.parse_cv_preview(data, cv.filename)


@router.post("/drafts", response_model=DraftOut, status_code=status.HTTP_201_CREATED)
async def create_draft(user: CandidateEditor, session: Session) -> DraftOut:
    """Start an empty draft (24h). Dropped CVs live here until saved or cancelled."""
    return await drafts_service.create_draft(session, user)


@router.post(
    "/drafts/{draft_id}/files",
    response_model=DraftFileUploadOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_draft_file(
    draft_id: uuid.UUID,
    user: CandidateEditor,
    session: Session,
    cv: Annotated[UploadFile, File()],
) -> DraftFileUploadOut:
    """Store a CV in the draft area and return its parsed fields. Creates no candidate."""
    data = await cv.read(MAX_CV_BYTES + 1)
    return await drafts_service.upload_draft_file(session, user, draft_id, data, cv.filename)


@router.delete("/drafts/{draft_id}", response_model=DraftDeleteOut)
async def delete_draft(
    draft_id: uuid.UUID, user: CandidateEditor, session: Session
) -> DraftDeleteOut:
    """Cancel a draft: delete its rows and the stored CVs."""
    return await drafts_service.delete_draft(session, user, draft_id)


@router.post("/drafts/{draft_id}/commit", response_model=DraftCommitOut)
async def commit_draft(
    draft_id: uuid.UUID, body: DraftCommitIn, user: CandidateEditor, session: Session
) -> DraftCommitOut:
    """Save draft rows as candidates + applications and move the CVs to permanent storage."""
    return await drafts_service.commit_draft(session, user, draft_id, body)


@router.get("/duplicates", response_model=DuplicateCheckOut)
async def check_duplicates(
    user: CandidateEditor,
    session: Session,
    email: Annotated[str | None, Query(max_length=320)] = None,
    phone: Annotated[str | None, Query(max_length=40)] = None,
) -> DuplicateCheckOut:
    return await analysis_service.find_duplicates(session, user, email=email, phone=phone)


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


@router.post("/bulk-delete", response_model=BulkCandidateDeleteOut)
async def bulk_delete_candidates(
    body: BulkCandidateDeleteRequest, user: AdminUser, session: Session, redis: RedisClient
) -> BulkCandidateDeleteOut:
    """Permanently delete candidates and all their data (admins only). Not reversible."""
    return await delete_service.hard_delete_candidates(
        session, redis, user, body.candidate_ids, bulk=True
    )


@router.delete("/{candidate_id}", response_model=CandidateDeleteOut)
async def delete_candidate(
    candidate_id: uuid.UUID, user: AdminUser, session: Session, redis: RedisClient
) -> CandidateDeleteOut:
    """Permanently delete one candidate and all their data (admins only). Not reversible."""
    return await delete_service.hard_delete_candidate(session, redis, user, candidate_id)


@router.patch("/{candidate_id}", response_model=CandidateOut)
async def patch_candidate(
    candidate_id: uuid.UUID, body: CandidatePatch, user: CandidateEditor, session: Session
) -> CandidateOut:
    """Edit any candidate profile field. Changes are logged on the timeline."""
    return await actions_service.update_candidate(session, user, candidate_id, body)


@router.post(
    "/{candidate_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    candidate_id: uuid.UUID,
    user: CandidateEditor,
    session: Session,
    file: Annotated[UploadFile, File()],
    doc_type: Annotated[str, Form()] = DocumentType.CV.value,
    application_id: Annotated[uuid.UUID | None, Form()] = None,
) -> DocumentOut:
    data = await file.read(MAX_CV_BYTES + 1)
    try:
        document_type = DocumentType(doc_type)
    except ValueError:
        document_type = DocumentType.OTHER
    return await documents_service.upload_candidate_document(
        session,
        user,
        candidate_id=candidate_id,
        file_bytes=data,
        file_name=file.filename,
        doc_type=document_type,
        application_id=application_id,
    )


@router.post("", response_model=ManualCandidateResult, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    user: CandidateEditor,
    session: Session,
    # Required fields are validated by ManualCandidateCreate so that missing, blank and
    # malformed values all return the same 422 `validation_error` with per-field details.
    first_name: Annotated[str | None, Form()] = None,
    last_name: Annotated[str | None, Form()] = None,
    email: Annotated[str | None, Form()] = None,
    phone: Annotated[str | None, Form()] = None,
    current_location: Annotated[str | None, Form()] = None,
    current_company: Annotated[str | None, Form()] = None,
    current_title: Annotated[str | None, Form()] = None,
    total_experience_years: Annotated[str | None, Form()] = None,
    notice_period_days: Annotated[int | None, Form()] = None,
    linkedin_url: Annotated[str | None, Form()] = None,
    portfolio_url: Annotated[str | None, Form()] = None,
    department_id: Annotated[uuid.UUID | None, Form()] = None,
    job_id: Annotated[str | None, Form()] = None,
    source: Annotated[str, Form()] = CandidateSource.MANUAL.value,
    tags: Annotated[str | None, Form()] = None,
    current_ctc_amount: Annotated[str | None, Form()] = None,
    current_ctc_currency: Annotated[str | None, Form()] = None,
    current_ctc_unit: Annotated[str | None, Form()] = None,
    current_ctc_negotiable: Annotated[bool | None, Form()] = None,
    expected_ctc_amount: Annotated[str | None, Form()] = None,
    expected_ctc_currency: Annotated[str | None, Form()] = None,
    expected_ctc_unit: Annotated[str | None, Form()] = None,
    expected_ctc_negotiable: Annotated[bool | None, Form()] = None,
    offered_ctc_amount: Annotated[str | None, Form()] = None,
    offered_ctc_currency: Annotated[str | None, Form()] = None,
    offered_ctc_unit: Annotated[str | None, Form()] = None,
    offered_ctc_negotiable: Annotated[bool | None, Form()] = None,
    cv: Annotated[UploadFile | None, File()] = None,
) -> ManualCandidateResult:
    """CAND-10: manual candidate create. Name, email, phone and job are required (B3)."""
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
    if total_experience_years:
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

    try:
        body = ManualCandidateCreate.model_validate(
            {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "current_location": current_location,
                "current_company": current_company,
                "current_title": current_title,
                "total_experience_years": years,
                "notice_period_days": notice_period_days,
                "linkedin_url": linkedin_url,
                "portfolio_url": portfolio_url,
                "department_id": department_id,
                "job_id": job_id,
                "source": source_enum,
                "tags": tag_list,
                "current_ctc": _salary_from_form(
                    current_ctc_amount,
                    current_ctc_currency,
                    current_ctc_unit,
                    current_ctc_negotiable,
                ),
                "expected_ctc": _salary_from_form(
                    expected_ctc_amount,
                    expected_ctc_currency,
                    expected_ctc_unit,
                    expected_ctc_negotiable,
                ),
                "offered_ctc": _salary_from_form(
                    offered_ctc_amount,
                    offered_ctc_currency,
                    offered_ctc_unit,
                    offered_ctc_negotiable,
                ),
            }
        )
    except ValidationError as exc:
        raise validation_app_error(exc) from exc
    cv_bytes = await cv.read() if cv is not None else None
    cv_name = cv.filename if cv is not None else None
    return await analysis_service.create_manual_candidate(session, user, body, cv_bytes, cv_name)
