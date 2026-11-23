"""ADM-03: anonymize and soft-delete stale rejected candidates when RETENTION_REJECTED_DAYS > 0."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.config import get_settings
from app.models import Application, Candidate, Document
from app.models.enums import ApplicationStatus
from app.services.compliance import write_audit

logger = logging.getLogger(__name__)


async def _eligible_candidate_ids(session: AsyncSession, cutoff: datetime) -> list[uuid.UUID]:
    """Candidates with a rejected application before cutoff and no active or hired applications."""
    stale_rejected = (
        select(Application.candidate_id)
        .where(
            Application.status == ApplicationStatus.REJECTED,
            Application.stage_entered_at < cutoff,
        )
        .distinct()
    )
    open_apps = select(Application.candidate_id).where(
        Application.status.in_((ApplicationStatus.ACTIVE, ApplicationStatus.HIRED))
    )
    rows = await session.scalars(
        select(Candidate.id).where(
            Candidate.id.in_(stale_rejected),
            Candidate.id.not_in(open_apps),
            Candidate.anonymized_at.is_(None),
            Candidate.deleted_at.is_(None),
        )
    )
    return list(rows)


async def run_retention_rejected(session: AsyncSession) -> dict[str, int | bool | str]:
    days = get_settings().retention_rejected_days
    if days <= 0:
        return {"enabled": False, "processed": 0}

    cutoff = datetime.now(UTC) - timedelta(days=days)
    candidate_ids = await _eligible_candidate_ids(session, cutoff)
    processed = 0
    now = datetime.now(UTC)

    for candidate_id in candidate_ids:
        candidate = await session.get(Candidate, candidate_id)
        if candidate is None:
            continue
        docs = list(
            await session.scalars(select(Document).where(Document.candidate_id == candidate_id))
        )
        for doc in docs:
            try:
                await storage.delete_object(doc.storage_key)
            except OSError:
                logger.warning(
                    "retention_delete_object_failed key=%s", doc.storage_key, exc_info=True
                )

        candidate.first_name = "Anonymized"
        candidate.last_name = "Candidate"
        candidate.email = f"anon-{candidate.id}@invalid.local"
        candidate.phone = None
        candidate.linkedin_url = None
        candidate.portfolio_url = None
        candidate.current_company = None
        candidate.current_location = None
        candidate.anonymized_at = now
        candidate.deleted_at = now

        await write_audit(
            session,
            actor_id=None,
            action="retention.candidate_anonymized",
            entity_type="candidate",
            entity_id=candidate_id,
            diff={"retention_rejected_days": days},
        )
        processed += 1

    await session.commit()
    logger.info("retention_rejected_complete processed=%s cutoff=%s", processed, cutoff.isoformat())
    result: dict[str, int | bool | str] = {
        "enabled": True,
        "processed": processed,
        "cutoff": cutoff.isoformat(),
    }
    return result
