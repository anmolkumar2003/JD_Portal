from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class NoteCreate(BaseModel):
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]
    application_id: UUID | None = None
    mentions: list[UUID] = Field(default_factory=list)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    candidate_id: UUID
    application_id: UUID | None
    author_id: UUID
    author_name: str | None = None
    body: str
    mentions: list[UUID]
    created_at: datetime


class EmailTemplateIn(BaseModel):
    key: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    subject: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    body_html: Annotated[str, StringConstraints(min_length=1)]
    variables: list[str] = Field(default_factory=list)
    trigger_stage_id: UUID | None = None
    is_active: bool = True


class EmailTemplateOut(EmailTemplateIn):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID


class EmailPreviewIn(BaseModel):
    subject: str
    body_html: str
    variables: dict[str, str] = Field(default_factory=dict)


class EmailPreviewOut(BaseModel):
    subject: str
    body_html: str


class EmailSendIn(BaseModel):
    candidate_id: UUID
    application_id: UUID | None = None
    template_key: str | None = None
    to: Annotated[str, StringConstraints(min_length=3, max_length=320)] | None = None
    subject: str
    body: str


class EmailLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    candidate_id: UUID
    application_id: UUID | None
    template_key: str | None
    to_address: str
    subject: str
    body: str
    status: str
    sent_at: datetime


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime


class BulkActionIn(BaseModel):
    action: Annotated[str, StringConstraints(pattern=r"^(move_stage|reject|tag|shortlist)$")]
    application_ids: list[UUID] = Field(min_length=1, max_length=100)
    stage_id: UUID | None = None
    reason: str | None = None
    tags: list[str] = Field(default_factory=list)


class BulkActionOut(BaseModel):
    updated: int
