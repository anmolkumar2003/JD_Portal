import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import CandidateSource


class CandidateSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    current_location: str | None = None
    current_company: str | None = None
    current_title: str | None = None
    total_experience_years: Decimal | None = None
    expected_ctc: Decimal | None = None
    notice_period_days: int | None = None
    linkedin_url: str | None = None
    source: CandidateSource
    tags: list[str] = []


class TimelineActor(BaseModel):
    id: uuid.UUID
    full_name: str


class TimelineEvent(BaseModel):
    id: uuid.UUID
    action: str
    occurred_at: datetime
    application_id: uuid.UUID | None = None
    actor: TimelineActor | None = None
    meta: dict[str, Any] = {}
