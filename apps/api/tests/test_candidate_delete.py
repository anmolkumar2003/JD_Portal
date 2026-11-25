"""Permanent candidate deletion: RBAC, full cascade, audit without PII, storage + Redis."""

import json
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session

from app.core.redis import DELETED_CANDIDATES_KEY
from app.models import (
    ActivityLog,
    Application,
    AtsCheck,
    AuditLog,
    Candidate,
    ConsentRecord,
    Document,
    Interview,
    InterviewPanel,
    InterviewRating,
    MatchResult,
    Note,
    Notification,
    OrphanStorageObject,
    ParsedProfile,
    Scorecard,
    User,
)
from app.models.interviews import InterviewMode, InterviewType, Recommendation
from app.services import cv_processing
from app.services.storage_cleanup import cleanup_orphan_storage_sync
from tests.conftest import DEMO_EMAIL_DOMAIN, FakeRedis, _test_database_url, login
from tests.test_apply import _apply, _form


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _count(session: AsyncSession, model: Any, **where: Any) -> int:
    stmt = select(func.count()).select_from(model)
    for column, value in where.items():
        stmt = stmt.where(getattr(model, column) == value)
    return int(await session.scalar(stmt) or 0)


async def _seed_candidate(
    client: AsyncClient, db: async_sessionmaker[AsyncSession], email: str
) -> uuid.UUID:
    """Apply through the public form, then attach one row to every dependent table."""
    response = await _apply(client, data=_form(email))
    assert response.status_code == 201, response.text
    async with db() as session:
        candidate = await session.scalar(select(Candidate).where(Candidate.email == email))
        assert candidate is not None
        application = await session.scalar(
            select(Application).where(Application.candidate_id == candidate.id)
        )
        document = await session.scalar(
            select(Document).where(Document.candidate_id == candidate.id)
        )
        manager = await session.scalar(
            select(User).where(User.email == f"manager@{DEMO_EMAIL_DOMAIN}")
        )
        assert application is not None and document is not None and manager is not None

        session.add_all(
            [
                AtsCheck(document_id=document.id, score=80, checks=[], engine_version="t"),
                MatchResult(
                    application_id=application.id,
                    overall_score=70,
                    engine_version="t",
                    inputs_hash="0" * 64,
                ),
                Note(
                    candidate_id=candidate.id,
                    application_id=application.id,
                    author_id=manager.id,
                    body="note",
                ),
                Notification(
                    user_id=manager.id,
                    type="mention",
                    payload={"candidate_id": str(candidate.id)},
                ),
                ConsentRecord(candidate_id=candidate.id, purpose="recruitment", version="1"),
                ActivityLog(candidate_id=candidate.id, action="test.event"),
                InterviewRating(
                    org_id=candidate.org_id,
                    application_id=application.id,
                    round_name="R1",
                    interviewed_at=datetime.now(UTC),
                    interviewer_name="Someone",
                    overall_rating=4,
                    recommendation=Recommendation.YES,
                ),
            ]
        )
        interview = Interview(
            application_id=application.id,
            round_name="R1",
            type=InterviewType.TECHNICAL,
            mode=InterviewMode.VIDEO,
            scheduled_at=datetime.now(UTC),
            created_by=manager.id,
        )
        session.add(interview)
        await session.flush()
        session.add_all(
            [
                InterviewPanel(interview_id=interview.id, user_id=manager.id),
                Scorecard(interview_id=interview.id, interviewer_id=manager.id),
            ]
        )
        await session.commit()
        return candidate.id


@pytest.mark.usefixtures("db", "sent_emails", "stored_objects")
@pytest.mark.parametrize("handle", ["recruiter", "manager", "interviewer"])
async def test_only_admins_can_delete(
    client: AsyncClient, db: async_sessionmaker[AsyncSession], handle: str
) -> None:
    candidate_id = await _seed_candidate(client, db, "rbac@example.com")
    token = await login(client, handle)

    single = await client.delete(f"/api/v1/candidates/{candidate_id}", headers=_auth(token))
    bulk = await client.post(
        "/api/v1/candidates/bulk-delete",
        headers=_auth(token),
        json={"candidate_ids": [str(candidate_id)]},
    )

    assert single.status_code == 403
    assert bulk.status_code == 403
    async with db() as session:
        assert await _count(session, Candidate, id=candidate_id) == 1


@pytest.mark.usefixtures("sent_emails")
@pytest.mark.parametrize("handle", ["hradmin", "superadmin"])
async def test_admin_hard_deletes_everything_and_audits_counts_only(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    stored_objects: dict[str, bytes],
    fake_redis: FakeRedis,
    handle: str,
) -> None:
    email = "erase.me@example.com"
    candidate_id = await _seed_candidate(client, db, email)
    other_id = await _seed_candidate(client, db, "keep.me@example.com")
    assert len(stored_objects) == 2
    token = await login(client, handle)

    response = await client.delete(f"/api/v1/candidates/{candidate_id}", headers=_auth(token))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(candidate_id) and body["deleted"] is True
    counts = body["counts"]
    for table in (
        "candidates",
        "applications",
        "documents",
        "parsed_profiles",
        "ats_checks",
        "match_results",
        "notes",
        "notifications",
        "interviews",
        "interview_panel",
        "scorecards",
        "interview_ratings",
        "consent_records",
    ):
        assert counts[table] >= 1, table
    assert counts["storage_objects_deleted"] == 1 and counts["storage_objects_orphaned"] == 0

    assert len(stored_objects) == 1  # only the other candidate's CV is left
    assert str(candidate_id) in fake_redis.sets[DELETED_CANDIDATES_KEY]
    assert fake_redis.ttls[DELETED_CANDIDATES_KEY] > 0

    async with db() as session:
        assert await _count(session, Candidate, id=candidate_id) == 0
        assert await _count(session, Application, candidate_id=candidate_id) == 0
        assert await _count(session, Document, candidate_id=candidate_id) == 0
        assert await _count(session, ParsedProfile, candidate_id=candidate_id) == 0
        assert await _count(session, Note, candidate_id=candidate_id) == 0
        assert await _count(session, ConsentRecord, candidate_id=candidate_id) == 0
        assert await _count(session, ActivityLog, candidate_id=candidate_id) == 0
        # Unrelated data is untouched, including the other candidate's notification.
        assert await _count(session, Candidate, id=other_id) == 1
        assert await _count(session, Notification) == 1
        assert await _count(session, Interview) == 1

        audit = await session.scalar(select(AuditLog).where(AuditLog.entity_id == candidate_id))
        assert audit is not None
        assert audit.action == "candidate.deleted" and audit.entity_type == "candidate"
        assert audit.diff["counts"]["candidates"] == 1
        assert "erase" not in json.dumps(audit.diff).lower()
        assert email not in json.dumps(audit.diff)


@pytest.mark.usefixtures("db", "sent_emails")
async def test_delete_unknown_candidate_is_404(client: AsyncClient) -> None:
    token = await login(client, "hradmin")

    response = await client.delete(f"/api/v1/candidates/{uuid.uuid4()}", headers=_auth(token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.usefixtures("sent_emails", "stored_objects")
async def test_bulk_delete_reports_deleted_and_failed(
    client: AsyncClient, db: async_sessionmaker[AsyncSession]
) -> None:
    first = await _seed_candidate(client, db, "bulk1@example.com")
    second = await _seed_candidate(client, db, "bulk2@example.com")
    missing = uuid.uuid4()
    token = await login(client, "hradmin")

    response = await client.post(
        "/api/v1/candidates/bulk-delete",
        headers=_auth(token),
        json={"candidate_ids": [str(first), str(second), str(missing), str(first)]},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["id"] for item in body["deleted"]] == [str(first), str(second)]
    assert all(item["deleted"] for item in body["deleted"])
    assert [(f["id"], f["code"]) for f in body["failed"]] == [(str(missing), "not_found")]
    async with db() as session:
        for candidate_id in (first, second):
            assert await _count(session, Candidate, id=candidate_id) == 0
        actions = set(
            await session.scalars(
                select(AuditLog.action).where(AuditLog.entity_type == "candidate")
            )
        )
        assert "candidate.bulk_deleted" in actions
        assert "candidate.deleted" not in actions


@pytest.mark.usefixtures("db")
async def test_bulk_delete_rejects_empty_list(client: AsyncClient) -> None:
    token = await login(client, "hradmin")

    response = await client.post(
        "/api/v1/candidates/bulk-delete", headers=_auth(token), json={"candidate_ids": []}
    )

    assert response.status_code == 422


@pytest.mark.usefixtures("sent_emails")
async def test_failed_storage_delete_is_queued_for_retry(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    stored_objects: dict[str, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_id = await _seed_candidate(client, db, "orphan@example.com")
    (key,) = stored_objects

    async def broken_delete(key: str) -> None:
        raise OSError("minio down")

    monkeypatch.setattr("app.core.storage.delete_object", broken_delete)
    token = await login(client, "hradmin")

    response = await client.delete(f"/api/v1/candidates/{candidate_id}", headers=_auth(token))

    assert response.status_code == 200, response.text
    assert response.json()["counts"]["storage_objects_orphaned"] == 1
    async with db() as session:
        assert await _count(session, Candidate, id=candidate_id) == 0
        orphan = await session.scalar(select(OrphanStorageObject))
        assert orphan is not None and orphan.storage_key == key


@pytest.mark.usefixtures("db")
def test_cleanup_job_retries_and_clears_orphans(monkeypatch: pytest.MonkeyPatch) -> None:
    deleted: list[str] = []

    def delete_object_sync(key: str) -> None:
        if key == "bad":
            raise OSError("still down")
        deleted.append(key)

    monkeypatch.setattr("app.core.storage.delete_object_sync", delete_object_sync)
    url = _test_database_url().replace("+asyncpg", "+psycopg")
    engine = create_engine(url)
    with Session(engine) as session:
        session.add_all(
            [OrphanStorageObject(storage_key="good"), OrphanStorageObject(storage_key="bad")]
        )
        session.commit()

        result = cleanup_orphan_storage_sync(session)

        assert result == {"processed": 2, "removed": 1, "failed": 1}
        assert deleted == ["good"]
        left = session.scalars(select(OrphanStorageObject)).all()
        assert [(o.storage_key, o.attempts, o.last_error) for o in left] == [("bad", 1, "OSError")]
    engine.dispose()


# --- CV worker guard (pure unit tests, no database) -------------------------------------------


def _session_returning(document: object | None, candidate: object | None) -> MagicMock:
    session = MagicMock()
    session.get.side_effect = lambda model, _id: document if model is Document else candidate
    return session


def test_process_document_skips_missing_document() -> None:
    session = _session_returning(None, None)

    cv_processing.process_document_sync(session, uuid.uuid4())

    session.add.assert_not_called()
    session.scalar.assert_not_called()


def test_process_document_skips_missing_candidate() -> None:
    document = MagicMock(candidate_id=uuid.uuid4())
    session = _session_returning(document, None)

    cv_processing.process_document_sync(session, uuid.uuid4())

    session.add.assert_not_called()
    session.scalar.assert_not_called()


def test_process_document_skips_candidate_marked_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    document = MagicMock(candidate_id=uuid.uuid4())
    session = _session_returning(document, MagicMock())
    monkeypatch.setattr(cv_processing, "is_candidate_marked_deleted_sync", lambda _id: True)

    cv_processing.process_document_sync(session, uuid.uuid4())

    session.add.assert_not_called()
    session.scalar.assert_not_called()
    assert document.mock_calls == []
