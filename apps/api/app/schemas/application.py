from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models.enums import (
    ApplicationStatus,
    BudgetStatus,
    CandidateSource,
    DocumentType,
    ParseStatus,
    SalaryUnit,
    StageType,
)
from app.schemas.job import NamedRef
from app.schemas.salary import SalaryIn, SalaryOut

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Phone = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=6, max_length=40, pattern=r"^\+?[0-9 ()\-.]+$"
    ),
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

    @field_validator("linkedin_url", mode="before")
    @classmethod
    def _check_url(cls, value: object) -> str | None:
        from app.schemas.linkedin import normalize_linkedin_url

        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("LinkedIn URL must be a string")
        return normalize_linkedin_url(value)

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


# --- Portal applications (CAND-01..04, CAND-09, PIPE-01/02) ------------------------------------


class ApplicationFilters(BaseModel):
    job_id: UUID | None = None
    stage_id: UUID | None = None
    candidate_id: UUID | None = None
    # The candidate's own department, or the job's when HR has not set one.
    department_id: UUID | None = None
    q: str | None = Field(default=None, max_length=200)
    source: CandidateSource | None = None
    applied_from: date | None = None
    applied_to: date | None = None
    score_min: Annotated[int, Field(ge=0, le=100)] | None = None
    score_max: Annotated[int, Field(ge=0, le=100)] | None = None
    skill: str | None = Field(default=None, max_length=100)
    # Multi-select skills; when set, overrides single `skill` for filtering.
    skills: list[str] = Field(default_factory=list)
    skills_mode: Annotated[str, Field(pattern="^(any|all)$")] = "any"
    tag: str | None = Field(default=None, max_length=50)
    is_shortlisted: bool | None = None
    location: str | None = Field(default=None, max_length=200)
    experience_min: Annotated[float, Field(ge=0, le=60)] | None = None
    experience_max: Annotated[float, Field(ge=0, le=60)] | None = None
    notice_min_days: Annotated[int, Field(ge=0, le=730)] | None = None
    notice_max_days: Annotated[int, Field(ge=0, le=730)] | None = None
    expected_ctc_min: Annotated[Decimal, Field(ge=0)] | None = None
    expected_ctc_max: Annotated[Decimal, Field(ge=0)] | None = None
    expected_ctc_currency: Annotated[str, Field(min_length=3, max_length=3)] | None = None
    expected_ctc_unit: SalaryUnit | None = None
    ats_score_min: Annotated[int, Field(ge=0, le=100)] | None = None
    ats_score_max: Annotated[int, Field(ge=0, le=100)] | None = None
    rating_min: Annotated[float, Field(ge=1, le=5)] | None = None
    rating_max: Annotated[float, Field(ge=1, le=5)] | None = None
    status: ApplicationStatus | None = None


class StageRef(BaseModel):
    id: UUID
    name: str
    type: StageType
    order: int


class ApplicationListItem(BaseModel):
    id: UUID
    reference_no: str
    status: ApplicationStatus
    candidate_id: UUID
    first_name: str
    last_name: str
    email: str
    current_title: str | None
    current_company: str | None
    source: CandidateSource
    job: NamedRef
    stage: StageRef
    overall_score: int | None
    overall_rating: Decimal | None = None
    is_shortlisted: bool = False
    tags: list[str] = Field(default_factory=list)
    expected_ctc: Decimal | None = None
    budget_status: BudgetStatus = BudgetStatus.UNKNOWN
    applied_at: datetime
    stage_entered_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: DocumentType
    file_name: str
    mime_type: str
    size: int
    is_primary: bool


class ParsedProfileOut(BaseModel):
    id: UUID | None = None
    document_id: UUID | None = None
    parse_status: ParseStatus
    data: dict[str, Any]
    corrected_data: dict[str, Any] | None = None
    total_experience_years: Decimal | None
    confidence: dict[str, Any]
    error: str | None
    parser_version: str | None = None


class AtsCheckOut(BaseModel):
    score: int
    checks: list[dict[str, Any]]
    engine_version: str
    band: str | None = None


class MatchResultOut(BaseModel):
    overall_score: int
    breakdown: dict[str, Any]
    matched_skills: list[str]
    missing_required: list[str]
    missing_preferred: list[str]
    extra_skills: list[str]
    explanation: dict[str, Any]
    engine_version: str
    computed_at: datetime


class AnalysisOut(BaseModel):
    """GET /applications/{id}/analysis — parsed profile, ATS check, match (CV-04..07)."""

    application_id: UUID
    document_id: UUID | None
    parsed_profile: ParsedProfileOut | None
    ats_check: AtsCheckOut | None
    match_result: MatchResultOut | None
    disclaimer: str = "Score is advisory; a recruiter makes the decision."


class ParsedProfilePatch(BaseModel):
    """Recruiter corrections (CV-08). Partial overlay stored in corrected_data."""

    data: dict[str, Any]
    total_experience_years: Annotated[Decimal, Field(ge=0, le=50, decimal_places=1)] | None = None


class ManualCandidateCreate(BaseModel):
    """CAND-10: HR creates a candidate (optionally linked to a job) with CV upload."""

    first_name: Name
    last_name: Name
    email: EmailStr
    phone: Phone
    current_location: ShortText | None = None
    current_company: ShortText | None = None
    current_title: ShortText | None = None
    total_experience_years: Annotated[Decimal, Field(ge=0, le=50, decimal_places=1)] | None = None
    notice_period_days: Annotated[int, Field(ge=0, le=365)] | None = None
    linkedin_url: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None
    ) = None
    portfolio_url: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None
    ) = None
    # Department is taken from the job; this is only a fallback when the job has none.
    department_id: UUID | None = None
    job_id: UUID
    source: CandidateSource = CandidateSource.MANUAL
    tags: list[str] = Field(default_factory=list)
    current_ctc: SalaryIn | None = None
    expected_ctc: SalaryIn | None = None
    offered_ctc: SalaryIn | None = None

    @field_validator("first_name", "last_name", "email", "phone", "job_id", mode="before")
    @classmethod
    def _required(cls, value: object) -> object:
        """B3: blank and missing give the same clear message as a missing field."""
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError("This field is required")
        return value

    @field_validator("linkedin_url", mode="before")
    @classmethod
    def _linkedin(cls, value: object) -> str | None:
        from app.schemas.linkedin import normalize_linkedin_url

        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("LinkedIn URL must be a string")
        return normalize_linkedin_url(value)

    @field_validator("portfolio_url", mode="before")
    @classmethod
    def _portfolio(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Portfolio URL must be a string")
        text = value.strip()
        if not text:
            return None
        if not text.lower().startswith(("https://", "http://")):
            raise ValueError("Must be a full URL starting with https://")
        return text[:500]


class ManualCandidateResult(BaseModel):
    candidate_id: UUID
    application_id: UUID | None = None
    document_id: UUID | None = None
    reference_no: str | None = None
    reused: bool = False
    budget_status: BudgetStatus = BudgetStatus.UNKNOWN


class CvParseOut(BaseModel):
    """Fields extracted from a CV for form autofill. Nothing is saved."""

    file_name: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    current_location: str | None = None
    current_company: str | None = None
    current_title: str | None = None
    total_experience_years: float | None = None
    linkedin_url: str | None = None
    skills: list[str] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)


class DuplicateMatch(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None
    matched_on: list[str]


class DuplicateCheckOut(BaseModel):
    matches: list[DuplicateMatch]


class ReprocessOut(BaseModel):
    document_id: UUID
    status: str = "queued"


class RescoreOut(BaseModel):
    job_id: UUID
    status: str = "queued"


class CandidateSummary(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None
    current_location: str | None
    current_company: str | None
    current_title: str | None
    total_experience_years: Decimal | None
    expected_ctc: Decimal | None
    current_salary: SalaryOut | None = None
    expected_salary: SalaryOut | None = None
    offered_salary: SalaryOut | None = None
    notice_period_days: int | None
    linkedin_url: str | None
    portfolio_url: str | None = None
    department_id: UUID | None = None
    source: CandidateSource
    tags: list[str]


class ApplicationOut(BaseModel):
    id: UUID
    reference_no: str
    status: ApplicationStatus
    rejection_reason: str | None
    cover_letter: str | None
    applied_at: datetime
    stage_entered_at: datetime
    is_shortlisted: bool
    candidate: CandidateSummary
    job: NamedRef
    stage: StageRef
    documents: list[DocumentOut]
    parsed_profile: ParsedProfileOut | None
    match_result: MatchResultOut | None
    budget_status: BudgetStatus = BudgetStatus.UNKNOWN
    job_salary_min: Decimal | None = None
    job_salary_max: Decimal | None = None
    job_salary_currency: str | None = None


ReasonText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class StagePatch(BaseModel):
    stage_id: UUID
    reason: ReasonText | None = None


class BoardCard(BaseModel):
    id: UUID
    candidate_id: UUID
    first_name: str
    last_name: str
    current_title: str | None
    overall_score: int | None
    overall_rating: Decimal | None = None
    stage_entered_at: datetime
    applied_at: datetime
    reference_no: str
    budget_status: BudgetStatus = BudgetStatus.UNKNOWN


class BoardColumn(BaseModel):
    stage: StageRef
    count: int
    cards: list[BoardCard]


class BoardOut(BaseModel):
    job_id: UUID
    job_title: str
    stages: list[BoardColumn]


class TimelineEntry(BaseModel):
    id: UUID
    action: str
    occurred_at: datetime
    actor_name: str | None
    application_id: UUID | None
    meta: dict[str, Any]
