"""Permanent (hard) candidate deletion — admin only.

Flow per candidate:
  1. mark the id in the Redis set `cv:deleted_candidates` and best-effort revoke queued
     `process_document` tasks, so CV workers cannot recreate data;
  2. in ONE transaction delete the candidate and every dependent row (explicitly, so we can
     report counts), then write the audit entry (counts only — never name/email/phone/PII);
  3. after the commit, delete the MinIO objects; keys that fail are recorded in
     `orphan_storage_objects` and retried by the `cleanup_orphan_storage` Celery job.

AuditLog rows are append-only history and are never removed here.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, cast

import anyio
from fastapi import status
from redis.asyncio import Redis
from sqlalchemy import Delete, delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.errors import AppError
from app.core.redis import DELETED_CANDIDATES_KEY, DELETED_CANDIDATES_TTL_SECONDS
from app.models import (
    ActivityLog,
    Application,
    AtsCheck,
    Candidate,
    ConsentRecord,
    Document,
    EmailLog,
    Interview,
    InterviewPanel,
    InterviewRating,
    MatchResult,
    Note,
    Notification,
    Offer,
    OrphanStorageObject,
    ParsedProfile,
    Scorecard,
    User,
)
from app.schemas.candidate_delete import (
    BulkCandidateDeleteOut,
    CandidateDeleteFailure,
    CandidateDeleteOut,
)
from app.services.compliance import write_audit

logger = logging.getLogger(__name__)

NOT_FOUND = "not_found"
DELETE_FAILED = "delete_failed"
REVOKE_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class _Outcome:
    counts: dict[str, int]
    storage_keys: list[str]


async def _execute_delete(session: AsyncSession, stmt: Delete) -> int:
    executed = await session.execute(stmt.execution_options(synchronize_session=False))
    result = cast("CursorResult[Any]", executed)
    return int(result.rowcount)


def _not_found(candidate_id: uuid.UUID) -> CandidateDeleteFailure:
    return CandidateDeleteFailure(id=candidate_id, code=NOT_FOUND, message="Candidate not found")


# --- Step 1: stop CV processing ---------------------------------------------------------------


async def _mark_deleted(redis: Redis, candidate_ids: list[uuid.UUID]) -> None:
    """Best effort: if Redis is down the DB existence checks in the worker still apply."""
    if not candidate_ids:
        return
    try:
        await redis.sadd(  # type: ignore[misc]
            DELETED_CANDIDATES_KEY, *(str(i) for i in candidate_ids)
        )
        await redis.expire(DELETED_CANDIDATES_KEY, DELETED_CANDIDATES_TTL_SECONDS)
    except Exception:
        logger.warning("candidate_delete_redis_mark_failed", exc_info=True)


async def _unmark_deleted(redis: Redis, candidate_id: uuid.UUID) -> None:
    try:
        await redis.srem(DELETED_CANDIDATES_KEY, str(candidate_id))  # type: ignore[misc]
    except Exception:
        logger.warning("candidate_delete_redis_unmark_failed", exc_info=True)


def _revoke_cv_tasks_sync(document_ids: frozenset[str]) -> int:
    """Revoke queued/active `process_document` tasks for the given documents (best effort)."""
    from app.workers.celery_app import celery_app  # noqa: PLC0415 - keep Celery out of import time

    inspector = celery_app.control.inspect(timeout=1.0)
    revoked: set[str] = set()
    for snapshot in (inspector.active(), inspector.reserved(), inspector.scheduled()):
        for tasks in (snapshot or {}).values():
            for entry in tasks:
                request = cast("dict[str, Any]", entry.get("request", entry))
                if request.get("name") != "process_document":
                    continue
                task_id = request.get("id")
                haystack = f"{request.get('args')} {request.get('kwargs')}"
                if task_id and task_id not in revoked and any(d in haystack for d in document_ids):
                    celery_app.control.revoke(task_id)
                    revoked.add(str(task_id))
    return len(revoked)


async def revoke_cv_tasks(document_ids: list[uuid.UUID]) -> int:
    """Never raises: a missing broker/worker must not block a deletion."""
    if not document_ids:
        return 0
    wanted = frozenset(str(d) for d in document_ids)
    try:
        with anyio.fail_after(REVOKE_TIMEOUT_SECONDS):
            return await anyio.to_thread.run_sync(
                lambda: _revoke_cv_tasks_sync(wanted), abandon_on_cancel=True
            )
    except Exception:
        logger.warning("candidate_delete_revoke_failed", exc_info=True)
        return 0


# --- Step 2: the database transaction ---------------------------------------------------------


async def _delete_in_transaction(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    actor_id: uuid.UUID,
    candidate_id: uuid.UUID,
    bulk: bool,
) -> _Outcome | None:
    """Delete everything for one candidate and commit. Returns None if it no longer exists."""
    locked = await session.scalar(
        select(Candidate.id)
        .where(Candidate.id == candidate_id, Candidate.org_id == org_id)
        .with_for_update()
    )
    if locked is None:
        await session.rollback()
        return None

    app_ids = select(Application.id).where(Application.candidate_id == candidate_id)
    doc_ids = select(Document.id).where(Document.candidate_id == candidate_id)
    interview_ids = select(Interview.id).where(Interview.application_id.in_(app_ids))

    storage_keys = list(
        await session.scalars(select(Document.storage_key).where(Document.id.in_(doc_ids)))
    )

    counts: dict[str, int] = {
        "notifications": await _execute_delete(
            session,
            delete(Notification).where(
                Notification.payload["candidate_id"].as_string() == str(candidate_id)
            ),
        ),
        "scorecards": await _execute_delete(
            session, delete(Scorecard).where(Scorecard.interview_id.in_(interview_ids))
        ),
        "interview_panel": await _execute_delete(
            session, delete(InterviewPanel).where(InterviewPanel.interview_id.in_(interview_ids))
        ),
        "interviews": await _execute_delete(
            session, delete(Interview).where(Interview.application_id.in_(app_ids))
        ),
        "interview_ratings": await _execute_delete(
            session, delete(InterviewRating).where(InterviewRating.application_id.in_(app_ids))
        ),
        "offers": await _execute_delete(
            session, delete(Offer).where(Offer.application_id.in_(app_ids))
        ),
        "match_results": await _execute_delete(
            session, delete(MatchResult).where(MatchResult.application_id.in_(app_ids))
        ),
        "ats_checks": await _execute_delete(
            session, delete(AtsCheck).where(AtsCheck.document_id.in_(doc_ids))
        ),
        "parsed_profiles": await _execute_delete(
            session,
            delete(ParsedProfile).where(
                (ParsedProfile.candidate_id == candidate_id)
                | ParsedProfile.document_id.in_(doc_ids)
            ),
        ),
        "notes": await _execute_delete(
            session, delete(Note).where(Note.candidate_id == candidate_id)
        ),
        "email_logs": await _execute_delete(
            session, delete(EmailLog).where(EmailLog.candidate_id == candidate_id)
        ),
        "activity_logs": await _execute_delete(
            session,
            delete(ActivityLog).where(
                (ActivityLog.candidate_id == candidate_id) | ActivityLog.application_id.in_(app_ids)
            ),
        ),
        "consent_records": await _execute_delete(
            session, delete(ConsentRecord).where(ConsentRecord.candidate_id == candidate_id)
        ),
        "documents": await _execute_delete(
            session, delete(Document).where(Document.candidate_id == candidate_id)
        ),
        "applications": await _execute_delete(
            session, delete(Application).where(Application.candidate_id == candidate_id)
        ),
        "candidates": await _execute_delete(
            session, delete(Candidate).where(Candidate.id == candidate_id)
        ),
    }

    # Counts only. The candidate's name, email and phone must never reach the audit log.
    await write_audit(
        session,
        actor_id=actor_id,
        action="candidate.bulk_deleted" if bulk else "candidate.deleted",
        entity_type="candidate",
        entity_id=candidate_id,
        diff={"counts": counts, "storage_objects": len(storage_keys)},
    )
    await session.commit()
    return _Outcome(counts=counts, storage_keys=storage_keys)


# --- Step 3: object storage -------------------------------------------------------------------


async def _purge_storage(session: AsyncSession, keys: list[str]) -> tuple[int, int]:
    """Delete objects; queue failures for the retry job. Returns (deleted, orphaned)."""
    deleted = 0
    failed: list[str] = []
    for key in keys:
        try:
            await storage.delete_object(key)
            deleted += 1
        except Exception:
            logger.warning("candidate_delete_storage_failed key=%s", key, exc_info=True)
            failed.append(key)
    if failed:
        try:
            await session.execute(
                pg_insert(OrphanStorageObject)
                .values(
                    [
                        {"storage_key": key, "reason": "candidate_deleted", "attempts": 1}
                        for key in failed
                    ]
                )
                .on_conflict_do_nothing(index_elements=["storage_key"])
            )
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("candidate_delete_orphan_record_failed keys=%s", failed)
    return deleted, len(failed)


# --- Public API -------------------------------------------------------------------------------


async def hard_delete_candidates(
    session: AsyncSession,
    redis: Redis,
    actor: User,
    candidate_ids: list[uuid.UUID],
    *,
    bulk: bool,
) -> BulkCandidateDeleteOut:
    """Delete each candidate in its own transaction; failures never affect the others."""
    # Plain ids: a rollback expires ORM instances, and `actor` must not be touched afterwards.
    org_id, actor_id = actor.org_id, actor.id
    unique_ids = list(dict.fromkeys(candidate_ids))
    existing = set(
        await session.scalars(
            select(Candidate.id).where(Candidate.id.in_(unique_ids), Candidate.org_id == org_id)
        )
    )
    document_ids = list(
        await session.scalars(select(Document.id).where(Document.candidate_id.in_(existing)))
    )
    await session.rollback()  # end the read-only transaction before the real work

    await _mark_deleted(redis, [i for i in unique_ids if i in existing])
    await revoke_cv_tasks(document_ids)

    deleted: list[CandidateDeleteOut] = []
    failed: list[CandidateDeleteFailure] = []
    for candidate_id in unique_ids:
        if candidate_id not in existing:
            failed.append(_not_found(candidate_id))
            continue
        try:
            outcome = await _delete_in_transaction(
                session, org_id=org_id, actor_id=actor_id, candidate_id=candidate_id, bulk=bulk
            )
        except Exception:
            await session.rollback()
            await _unmark_deleted(redis, candidate_id)
            logger.exception("candidate_hard_delete_failed candidate_id=%s", candidate_id)
            failed.append(
                CandidateDeleteFailure(
                    id=candidate_id, code=DELETE_FAILED, message="Candidate could not be deleted"
                )
            )
            continue
        if outcome is None:
            failed.append(_not_found(candidate_id))
            continue
        removed, orphaned = await _purge_storage(session, outcome.storage_keys)
        deleted.append(
            CandidateDeleteOut(
                id=candidate_id,
                counts={
                    **outcome.counts,
                    "storage_objects_deleted": removed,
                    "storage_objects_orphaned": orphaned,
                },
            )
        )
    return BulkCandidateDeleteOut(deleted=deleted, failed=failed)


async def hard_delete_candidate(
    session: AsyncSession, redis: Redis, actor: User, candidate_id: uuid.UUID
) -> CandidateDeleteOut:
    result = await hard_delete_candidates(session, redis, actor, [candidate_id], bulk=False)
    if result.deleted:
        return result.deleted[0]
    code = result.failed[0].code if result.failed else DELETE_FAILED
    if code == NOT_FOUND:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Candidate not found")
    raise AppError(
        status.HTTP_500_INTERNAL_SERVER_ERROR, DELETE_FAILED, "Candidate could not be deleted"
    )
