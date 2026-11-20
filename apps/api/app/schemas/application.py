import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models.enums import ApplicationStatus, CandidateSource, DocumentType, ParseStatus
from app.schemas.candidate import CandidateSummary
from app.schemas.job import NamedRef
from app.schemas.org import PipelineStageOut

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Phone = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=6, max_length=40, pattern=r"^\+?[0-9 ()\-.]+$"
    ),
]
RejectionReason = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=3, max_length=2000)
]


class ApplyForm(BaseModel):
    """Multipart text fields of the public apply form (APPLY-02/03)."""

    first_name: Name
    last_name: Name
    email: EmailStr
    phone: Phone
    current_location: ShortText | None = None
    current_company: ShortText | None = None
    current_title: ShortText | None = None
    total_experience_years: Annotated[Decimal, Field(ge=0, le=50, decimal_places=1)] | None = None
    expected_ctc: Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)] | None = None
    notice_period_days: Annotated[int, Field(ge=0, le=365)] | None = None
    linkedin_url: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None
    ) = None
    cover_letter: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)] | None
    ) = None
    consent: bool
    # Honeypot: hidden from people, so any value means a bot filled the form.
    website: str = ""

    @model_validator(mode="before")
    @classmethod
    def _blank_to_none(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {
                k: (None if isinstance(v, str) and not v.strip() and k != "website" else v)
                for k, v in data.items()
            }
        return data

    @field_validator("linkedin_url")
    @classmethod
    def _check_url(cls, value: str | None) -> str | None:
        if value is not None and not value.lower().startswith(("https://", "http://")):
            raise ValueError("Must be a full URL starting with https://")
        return value

    @field_validator("consent")
    @classmethod
    def _require_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Consent is required to apply")
        return value


class ApplyResult(BaseModel):
    reference_no: str
    job_title: str


class DownloadUrlOut(BaseModel):
    url: str
    expires_in: int
    file_name: str


# --- Portal applications (CAND / PIPE) --------------------------------------------------------


class ApplicationFilters(BaseModel):
    job_id: uuid.UUID | None = None
    stage_id: uuid.UUID | None = None
    candidate_id: uuid.UUID | None = None
    q: str | None = None
    source: CandidateSource | None = None
    applied_from: datetime | None = None
    applied_to: datetime | None = None


class ApplicationListItem(BaseModel):
    id: uuid.UUID
    reference_no: str
    status: ApplicationStatus
    applied_at: datetime
    stage_entered_at: datetime
    stage: PipelineStageOut
    job: NamedRef
    candidate: CandidateSummary
    overall_score: int | None = None
    source: CandidateSource


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: DocumentType
    file_name: str
    mime_type: str
    size: int
    is_primary: bool


class ParsedProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parse_status: ParseStatus
    data: dict[str, Any] = {}
    total_experience_years: Decimal | None = None
    error: str | None = None


class MatchResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    overall_score: int
    breakdown: dict[str, Any] = {}
    matched_skills: list[str] = []
    missing_required: list[str] = []
    missing_preferred: list[str] = []
    extra_skills: list[str] = []
    explanation: dict[str, Any] = {}
    engine_version: str
    computed_at: datetime


class ApplicationDetail(BaseModel):
    id: uuid.UUID
    reference_no: str
    status: ApplicationStatus
    applied_at: datetime
    stage_entered_at: datetime
    rejection_reason: str | None = None
    cover_letter: str | None = None
    stage: PipelineStageOut
    job: NamedRef
    candidate: CandidateSummary
    documents: list[DocumentOut]
    parsed_profile: ParsedProfileOut | None = None
    match_result: MatchResultOut | None = None


class StageChangeIn(BaseModel):
    stage_id: uuid.UUID
    rejection_reason: RejectionReason | None = None


class BoardCard(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    first_name: str
    last_name: str
    current_title: str | None = None
    stage_entered_at: datetime
    overall_score: int | None = None
    reference_no: str


class BoardColumn(BaseModel):
    stage: PipelineStageOut
    count: int
    cards: list[BoardCard]


class BoardOut(BaseModel):
    job_id: uuid.UUID
    stages: list[BoardColumn]
