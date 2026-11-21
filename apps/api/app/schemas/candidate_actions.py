"""Schemas for notes, tags, shortlist and bulk actions (CAND-05, CAND-06)."""

import enum
from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.models.enums import UserRole
from app.schemas.application import ReasonText

Tag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
NoteBody = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]

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
    """Editable candidate fields. Only tags for now (CAND-05)."""

    tags: list[Tag] = Field(max_length=MAX_TAGS)


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
