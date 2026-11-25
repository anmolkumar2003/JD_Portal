"""Temporary upload area for the Add Candidate flow (nothing here is a candidate yet)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin

DRAFT_TTL = timedelta(hours=24)


def draft_expiry() -> datetime:
    return datetime.now(UTC) + DRAFT_TTL


class CandidateDraft(Base, UUIDPrimaryKeyMixin):
    """A staging area for CVs dropped on the Add Candidate page.

    Files live in object storage under `drafts/<org>/<draft>/<file>.<ext>` until the draft is
    committed (files move to permanent keys), cancelled, or expires (`cleanup_expired_drafts`).
    """

    __tablename__ = "candidate_drafts"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=draft_expiry, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CandidateDraftFile(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "candidate_draft_files"

    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_drafts.id", ondelete="CASCADE"), index=True
    )
    storage_key: Mapped[str] = mapped_column(String(500))
    file_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(BigInteger)
    checksum: Mapped[str] = mapped_column(String(64))
    parsed_preview: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
