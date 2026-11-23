"""Schemas for notes, tags, shortlist, bulk actions and full candidate edits."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator, model_validator

from app.models.enums import CandidateSource, UserRole
from app.schemas.application import ReasonText
from app.schemas.linkedin import normalize_linkedin_url
from app.schemas.salary import SalaryIn, SalaryOut

Tag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
NoteBody = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Phone = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=6, max_length=40, pattern=r"^\+?[0-9 ()\-.]+$"
    ),
]
Url = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]

MAX_TAGS = 20
MAX_BULK_IDS = 100


class UserRef(BaseModel):
    """Minimal user reference for @mention pickers; exposes no email or auth data."""

    id: UUID
    full_name: str
    role: UserRole


class NoteCreate(BaseModel):
    body: NoteBody
    application_id: UUID | None = None
    mentions: list[UUID] = Field(default_factory=list, max_length=20)


class NoteOut(BaseModel):
    id: UUID
    candidate_id: UUID
    application_id: UUID | None
    author: UserRef | None
    body: str
    mentions: list[UserRef]
    created_at: datetime


class CandidatePatch(BaseModel):
    """Full editable candidate profile. Omit a field to leave it unchanged."""

    first_name: Name | None = None
    last_name: Name | None = None
    email: EmailStr | None = None
    phone: Phone | None = None
    current_location: ShortText | None = None
    current_company: ShortText | None = None
    current_title: ShortText | None = None
    total_experience_years: Annotated[Decimal, Field(ge=0, le=50, decimal_places=1)] | None = None
    notice_period_days: Annotated[int, Field(ge=0, le=365)] | None = None
    linkedin_url: Url | None = None
    portfolio_url: Url | None = None
    department_id: UUID | None = None
    source: CandidateSource | None = None
    tags: list[Tag] | None = Field(default=None, max_length=MAX_TAGS)
    current_ctc: SalaryIn | None = None
    expected_ctc: SalaryIn | None = None
    offered_ctc: SalaryIn | None = None

    @field_validator("linkedin_url", mode="before")
    @classmethod
    def _linkedin(cls, value: object) -> str | None:
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


class CandidateOut(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None
    current_location: str | None
    current_company: str | None
    current_title: str | None
    total_experience_years: Decimal | None
    notice_period_days: int | None
    linkedin_url: str | None
    portfolio_url: str | None
    department_id: UUID | None
    source: CandidateSource
    tags: list[str]
    current_salary: SalaryOut
    expected_salary: SalaryOut
    offered_salary: SalaryOut


class CandidateTagsOut(BaseModel):
    id: UUID
    tags: list[str]


class ShortlistPatch(BaseModel):
    """Explicit value, or omit to toggle."""

    shortlisted: bool | None = None


class ShortlistOut(BaseModel):
    application_id: UUID
    is_shortlisted: bool


class BulkActionType(enum.StrEnum):
    MOVE_STAGE = "move_stage"
    REJECT = "reject"
    TAG = "tag"


class BulkPayload(BaseModel):
    stage_id: UUID | None = None
    reason: ReasonText | None = None
    add_tags: list[Tag] = Field(default_factory=list, max_length=MAX_TAGS)
    remove_tags: list[Tag] = Field(default_factory=list, max_length=MAX_TAGS)


class BulkActionRequest(BaseModel):
    action: BulkActionType
    ids: list[UUID] = Field(min_length=1, max_length=MAX_BULK_IDS)
    payload: BulkPayload = Field(default_factory=BulkPayload)

    @model_validator(mode="after")
    def _check_payload(self) -> Self:
        payload = self.payload
        if self.action == BulkActionType.MOVE_STAGE and payload.stage_id is None:
            raise ValueError("payload.stage_id is required for move_stage")
        if self.action == BulkActionType.REJECT and not payload.reason:
            raise ValueError("payload.reason is required for reject")
        if self.action == BulkActionType.TAG and not (payload.add_tags or payload.remove_tags):
            raise ValueError("payload.add_tags or payload.remove_tags is required for tag")
        return self


class BulkFailure(BaseModel):
    id: UUID
    code: str
    message: str


class BulkActionResult(BaseModel):
    action: BulkActionType
    succeeded: list[UUID]
    failed: list[BulkFailure]
