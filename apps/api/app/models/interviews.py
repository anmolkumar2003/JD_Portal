"""Interviews and scorecards (INT-01..04, INT-06)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.models.enums import pg_enum


class InterviewType(enum.StrEnum):
    PHONE = "phone"
    TECHNICAL = "technical"
    MANAGERIAL = "managerial"
    HR = "hr"


class InterviewMode(enum.StrEnum):
    VIDEO = "video"
    ONSITE = "onsite"


class InterviewStatus(enum.StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class Recommendation(enum.StrEnum):
    STRONG_NO = "strong_no"
    NO = "no"
    MIXED = "mixed"
    YES = "yes"
    STRONG_YES = "strong_yes"


class Interview(BaseModel):
    __tablename__ = "interviews"

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    round_name: Mapped[str] = mapped_column(String(200))
    type: Mapped[InterviewType] = mapped_column(pg_enum(InterviewType, "interview_type"))
    mode: Mapped[InterviewMode] = mapped_column(pg_enum(InterviewMode, "interview_mode"))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_min: Mapped[int] = mapped_column(Integer, default=60, server_default="60")
    meeting_link: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[InterviewStatus] = mapped_column(
        pg_enum(InterviewStatus, "interview_status"),
        default=InterviewStatus.SCHEDULED,
        server_default=InterviewStatus.SCHEDULED.value,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


class InterviewPanel(BaseModel):
    __tablename__ = "interview_panel"
    __table_args__ = (UniqueConstraint("interview_id", "user_id", name="uq_interview_panel"),)

    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    feedback_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ScorecardTemplate(BaseModel):
    __tablename__ = "scorecard_templates"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    competencies: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )


class Scorecard(BaseModel):
    __tablename__ = "scorecards"
    __table_args__ = (
        UniqueConstraint(
            "interview_id", "interviewer_id", name="uq_scorecards_interview_interviewer"
        ),
    )

    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), index=True
    )
    interviewer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    ratings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    comments: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[Recommendation | None] = mapped_column(
        pg_enum(Recommendation, "recommendation")
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
