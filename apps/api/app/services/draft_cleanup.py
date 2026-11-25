"""Hourly clean-up of expired Add Candidate drafts (B1). Sync, because Celery workers are sync."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core import storage
from app.models import CandidateDraft, CandidateDraftFile, OrphanStorageObject

logger = logging.getLogger(__name__)

EXPIRED_BATCH_SIZE = 100


def draft_prefix(org_id: uuid.UUID, draft_id: uuid.UUID) -> str:
    return f"drafts/{org_id}/{draft_id}/"


def draft_file_key(
    org_id: uuid.UUID, draft_id: uuid.UUID, file_id: uuid.UUID, extension: str
) -> str:
    return f"{draft_prefix(org_id, draft_id)}{file_id}.{extension}"


def cleanup_expired_drafts_sync(
    session: Session, *, batch_size: int = EXPIRED_BATCH_SIZE
) -> dict[str, int]:
    """Delete drafts past `expires_at`: their MinIO objects first, then the rows.

    A key that cannot be deleted is queued in `orphan_storage_objects` so the draft row can
    still go (the orphan job keeps retrying).
    """
    drafts = list(
        session.scalars(
            select(CandidateDraft)
            .where(CandidateDraft.expires_at <= datetime.now(UTC))
            .order_by(CandidateDraft.expires_at)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
    )
    objects_removed = 0
    objects_orphaned = 0
    for draft in drafts:
        keys = set(
            session.scalars(
                select(CandidateDraftFile.storage_key).where(
                    CandidateDraftFile.draft_id == draft.id
                )
            )
        )
        try:
            keys.update(storage.list_prefix_sync(draft_prefix(draft.org_id, draft.id)))
        except Exception:
            logger.warning("draft_list_prefix_failed", exc_info=True)
        for key in sorted(keys):
            try:
                storage.delete_object_sync(key)
                objects_removed += 1
            except Exception:
                logger.warning("draft_expiry_storage_delete_failed", exc_info=True)
                objects_orphaned += 1
                session.execute(
                    pg_insert(OrphanStorageObject)
                    .values(storage_key=key, reason="draft_expired", attempts=1)
                    .on_conflict_do_nothing(index_elements=["storage_key"])
                )
        session.execute(delete(CandidateDraftFile).where(CandidateDraftFile.draft_id == draft.id))
        session.execute(delete(CandidateDraft).where(CandidateDraft.id == draft.id))
    session.commit()
    logger.info(
        "draft_cleanup drafts=%s objects_removed=%s objects_orphaned=%s",
        len(drafts),
        objects_removed,
        objects_orphaned,
    )
    return {
        "drafts": len(drafts),
        "objects_removed": objects_removed,
        "objects_orphaned": objects_orphaned,
    }
