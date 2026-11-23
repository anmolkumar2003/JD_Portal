"""Named saved filter sets for the candidates list (Phase 4)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class SavedFilter(BaseModel):
    __tablename__ = "saved_filters"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_saved_filters_user_id_name"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    # Snapshot of ApplicationFilters / URL query keys the UI cares about.
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
