"""Consent, export, anonymize, audit (ADM-01..03)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Application, Candidate, Document, User
from app.models.compliance import AuditLog, ConsentRecord


async def write_audit(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    diff: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            diff=diff or {},
            ip=ip,
        )
    )


async def export_candidate(
    session: AsyncSession, user: User, candidate_id: uuid.UUID
) -> dict[str, Any]:
    candidate = await session.get(Candidate, candidate_id)
    if candidate is None or candidate.org_id != user.org_id:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Candidate not found")
    apps = list(
        await session.scalars(select(Application).where(Application.candidate_id == candidate_id))
    )
    docs = list(
        await session.scalars(select(Document).where(Document.candidate_id == candidate_id))
    )
    consents = list(
        await session.scalars(
            select(ConsentRecord).where(ConsentRecord.candidate_id == candidate_id)
        )
    )
    await write_audit(
        session,
        actor_id=user.id,
        action="candidate.exported",
        entity_type="candidate",
        entity_id=candidate_id,
    )
    await session.commit()
    return {
        "candidate": {
            "id": str(candidate.id),
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "source": candidate.source.value,
        },
        "applications": [{"id": str(a.id), "reference_no": a.reference_no} for a in apps],
        "documents": [
            {"id": str(d.id), "file_name": d.file_name, "type": d.type.value} for d in docs
        ],
        "consents": [
            {"purpose": c.purpose, "version": c.version, "granted_at": c.granted_at.isoformat()}
            for c in consents
        ],
    }


async def anonymize_candidate(
    session: AsyncSession, user: User, candidate_id: uuid.UUID
) -> dict[str, str]:
    candidate = await session.get(Candidate, candidate_id)
    if candidate is None or candidate.org_id != user.org_id:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Candidate not found")
    candidate.first_name = "Anonymized"
    candidate.last_name = "Candidate"
    candidate.email = f"anon-{candidate.id}@invalid.local"
    candidate.phone = None
    candidate.linkedin_url = None
    candidate.portfolio_url = None
    candidate.current_company = None
    candidate.current_location = None
    candidate.anonymized_at = datetime.now(UTC)
    await write_audit(
        session,
        actor_id=user.id,
        action="candidate.anonymized",
        entity_type="candidate",
        entity_id=candidate_id,
    )
    await session.commit()
    return {"id": str(candidate_id), "status": "anonymized"}


async def list_audit_logs(
    session: AsyncSession, user: User, limit: int = 100
) -> list[dict[str, Any]]:
    """Return recent audit rows for actors in the caller's org only."""
    rows = await session.scalars(
        select(AuditLog)
        .join(User, User.id == AuditLog.actor_id)
        .where(User.org_id == user.org_id)
        .order_by(AuditLog.occurred_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": str(r.id),
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": str(r.entity_id) if r.entity_id else None,
            "occurred_at": r.occurred_at.isoformat(),
        }
        for r in rows
    ]
