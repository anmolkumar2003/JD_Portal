"""Retry deleting object-storage keys left behind by candidate hard-deletes."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import storage
from app.models import OrphanStorageObject

logger = logging.getLogger(__name__)

BATCH_SIZE = 200


def cleanup_orphan_storage_sync(
    session: Session, *, batch_size: int = BATCH_SIZE
) -> dict[str, int]:
    """Try to delete each queued key; remove the row on success, record the error otherwise.

    S3 DeleteObject is idempotent, so a key that is already gone counts as success.
    """
    rows = list(
        session.scalars(
            select(OrphanStorageObject)
            .order_by(OrphanStorageObject.last_attempt_at.asc().nullsfirst())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
    )
    removed = 0
    failed = 0
    for row in rows:
        row.attempts += 1
        row.last_attempt_at = datetime.now(UTC)
        try:
            storage.delete_object_sync(row.storage_key)
        except Exception as exc:
            row.last_error = type(exc).__name__[:200]
            failed += 1
            logger.warning("orphan_storage_retry_failed key=%s", row.storage_key, exc_info=True)
        else:
            session.delete(row)
            removed += 1
    session.commit()
    remaining = len(rows) - removed
    logger.info(
        "orphan_storage_cleanup removed=%s failed=%s remaining=%s", removed, failed, remaining
    )
    return {"processed": len(rows), "removed": removed, "failed": failed}
