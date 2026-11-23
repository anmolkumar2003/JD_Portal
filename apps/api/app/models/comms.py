"""Notes, email templates/logs, notifications (COMM, CAND-05, PIPE-03)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Note(BaseModel):
    __tablename__ = "notes"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(Text)
    mentions: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list, server_default="{}"
    )


class EmailTemplate(BaseModel):
    __tablename__ = "email_templates"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(100), index=True)
    subject: Mapped[str] = mapped_column(String(500))
    body_html: Mapped[str] = mapped_column(Text)
    variables: Mapped[list[str]] = mapped_column(ARRAY(String(100)), default=list, server_default="{}")
    trigger_stage_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pipeline_stages.id", ondelete="SET NULL"), index=True
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")


class EmailLog(BaseModel):
    __tablename__ = "email_logs"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    template_key: Mapped[str | None] = mapped_column(String(100))
    to_address: Mapped[str] = mapped_column("to", String(320))
    subject: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="sent", server_default="sent")
    sent_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(BaseModel):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
