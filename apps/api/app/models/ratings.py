"""Simple interview ratings — always available, even when ENABLE_INTERVIEWS is off."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.models.enums import pg_enum
from app.models.interviews import Recommendation


class InterviewRating(BaseModel):
    """Manual HR interview feedback. Advisory only — never auto-rejects."""

    __tablename__ = "interview_ratings"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    round_name: Mapped[str] = mapped_column(String(200))
    interviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    interviewer_name: Mapped[str] = mapped_column(String(200))
    interviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    mode: Mapped[str] = mapped_column(String(40), default="video", server_default="video")
    comments: Mapped[str | None] = mapped_column(Text)
    # [{ "skill": "Kotlin", "rating": 4 }] — rating null/omitted means not assessed
    skill_ratings: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    overall_rating: Mapped[int] = mapped_column(Integer)
    recommendation: Mapped[Recommendation] = mapped_column(
        pg_enum(Recommendation, "recommendation", create_type=False)
    )
    strengths: Mapped[str | None] = mapped_column(Text)
    concerns: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
