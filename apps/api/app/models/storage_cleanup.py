"""Object-storage keys whose deletion failed and must be retried (hard-delete follow-up)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class OrphanStorageObject(BaseModel):
    """A MinIO/S3 object that should no longer exist.

    Written when deleting the object failed after a candidate hard-delete committed. The
    `cleanup_orphan_storage` Celery job retries and removes the row once the object is gone.
    The key is `<org>/<candidate>/<document>.<ext>` (opaque ids only, never PII).
    """

    __tablename__ = "orphan_storage_objects"

    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    reason: Mapped[str] = mapped_column(
        String(100), default="candidate_deleted", server_default="candidate_deleted"
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(String(200))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
