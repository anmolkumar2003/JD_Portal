"""CAND-05 notes/tags/shortlist and CAND-06 bulk actions."""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import ActivityLog, Application, Candidate, PipelineStage
from app.models.enums import StageType
from app.schemas.candidate_actions import BulkActionRequest
from app.services.candidate_actions import normalize_tags
from tests.conftest import login
from tests.test_apply import _apply, _form

# --- Pure unit tests (no database) ------------------------------------------------------------


def test_normalize_tags_trims_and_dedupes_case_insensitively() -> None:
    assert normalize_tags([" Python ", "python", "", "Remote", "REMOTE"]) == ["Python", "Remote"]


def test_bulk_request_requires_payload_per_action() -> None:
    ids = [uuid.uuid4()]
    with pytest.raises(ValidationError):
        BulkActionRequest(action="move_stage", ids=ids)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        BulkActionRequest(action="reject", ids=ids, payload={})  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        BulkActionRequest(action="tag", ids=ids, payload={})  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        BulkActionRequest(action="tag", ids=[], payload={"add_tags": ["x"]})  # type: ignore[arg-type]
    ok = BulkActionRequest(action="tag", ids=ids, payload={"add_tags": ["x"]})  # type: ignore[arg-type]
    assert ok.payload.add_tags == ["x"]


# --- API tests (need Postgres; skipped when it is not reachable) ------------------------------


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _apply_as(client: AsyncClient, email: str) -> str:
    response = await _apply(client, data=_form(email))
    assert response.status_code == 201, response.text
    token = await login(client, "recruiter")
    listed = await client.get("/api/v1/applications", headers=_auth(token), params={"q": email})
    item: dict[str, Any] = listed.json()["items"][0]
    return str(item["id"])


@pytest.mark.usefixtures("db", "sent_emails", "stored_objects")
async def test_notes_with_mentions_and_activity_log(
    client: AsyncClient, db: async_sessionmaker[AsyncSession]
) -> None:
    application_id = await _apply_as(client, "notes@example.com")
    token = await login(client, "recruiter")
    detail = await client.get(f"/api/v1/applications/{application_id}", headers=_auth(token))
    candidate_id = detail.json()["candidate"]["id"]

    users = await client.get("/api/v1/users/lookup", headers=_auth(token))
    assert users.status_code == 200, users.text
    manager = next(u for u in users.json() if u["role"] == "hiring_manager")
    assert set(manager) == {"id", "full_name", "role"}

    created = await client.post(
        f"/api/v1/candidates/{candidate_id}/notes",
        headers=_auth(token),
        json={"body": "Great system design, @manager please review", "mentions": [manager["id"]]},
    )
    assert created.status_code == 201, created.text
    assert created.json()["mentions"][0]["id"] == manager["id"]
    assert created.json()["author"]["role"] == "recruiter"

    listed = await client.get(f"/api/v1/candidates/{candidate_id}/notes", headers=_auth(token))
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    bad = await client.post(
        f"/api/v1/candidates/{candidate_id}/notes",
        headers=_auth(token),
        json={"body": "hi", "mentions": [str(uuid.uuid4())]},
    )
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "invalid_mention"

    async with db() as session:
        logs = list(
            await session.scalars(select(ActivityLog).where(ActivityLog.action == "note.created"))
        )
        assert len(logs) == 1
        assert "system design" not in str(logs[0].meta)  # no free text (PII) in the log


@pytest.mark.usefixtures("db", "sent_emails", "stored_objects")
async def test_tags_patch_and_shortlist(
    client: AsyncClient, db: async_sessionmaker[AsyncSession]
) -> None:
    application_id = await _apply_as(client, "tags@example.com")
    token = await login(client, "recruiter")
    detail = await client.get(f"/api/v1/applications/{application_id}", headers=_auth(token))
    candidate_id = detail.json()["candidate"]["id"]

    patched = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=_auth(token),
        json={"tags": ["Python", "python", " senior "]},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["tags"] == ["Python", "senior"]

    star = await client.post(
        f"/api/v1/applications/{application_id}/shortlist", headers=_auth(token)
    )
    assert star.status_code == 200, star.text
    assert star.json()["is_shortlisted"] is True
    unstar = await client.post(
        f"/api/v1/applications/{application_id}/shortlist",
        headers=_auth(token),
        json={"shortlisted": False},
    )
    assert unstar.json()["is_shortlisted"] is False

    manager = await login(client, "manager")
    forbidden = await client.post(
        f"/api/v1/applications/{application_id}/shortlist", headers=_auth(manager)
    )
    assert forbidden.status_code == 403
    forbidden_tags = await client.patch(
        f"/api/v1/candidates/{candidate_id}", headers=_auth(manager), json={"tags": ["x"]}
    )
    assert forbidden_tags.status_code == 403

    async with db() as session:
        actions = set(
            await session.scalars(
                select(ActivityLog.action).where(
                    ActivityLog.candidate_id == uuid.UUID(candidate_id)
                )
            )
        )
        assert {"candidate.tags_updated", "application.shortlisted"} <= actions


@pytest.mark.usefixtures("db", "sent_emails", "stored_objects")
async def test_bulk_actions(client: AsyncClient, db: async_sessionmaker[AsyncSession]) -> None:
    first = await _apply_as(client, "bulk1@example.com")
    second = await _apply_as(client, "bulk2@example.com")
    token = await login(client, "recruiter")

    async with db() as session:
        stages = {s.type: s for s in await session.scalars(select(PipelineStage))}
        screening = str(stages[StageType.SCREENING].id)

    moved = await client.post(
        "/api/v1/applications/bulk-action",
        headers=_auth(token),
        json={
            "action": "move_stage",
            "ids": [first, second, str(uuid.uuid4())],
            "payload": {"stage_id": screening},
        },
    )
    assert moved.status_code == 200, moved.text
    body = moved.json()
    assert set(body["succeeded"]) == {first, second}
    assert len(body["failed"]) == 1 and body["failed"][0]["code"] == "not_found"

    tagged = await client.post(
        "/api/v1/applications/bulk-action",
        headers=_auth(token),
        json={"action": "tag", "ids": [first, second], "payload": {"add_tags": ["shortlisted-q4"]}},
    )
    assert tagged.status_code == 200, tagged.text
    assert len(tagged.json()["succeeded"]) == 2

    no_reason = await client.post(
        "/api/v1/applications/bulk-action",
        headers=_auth(token),
        json={"action": "reject", "ids": [first], "payload": {}},
    )
    assert no_reason.status_code == 422

    rejected = await client.post(
        "/api/v1/applications/bulk-action",
        headers=_auth(token),
        json={"action": "reject", "ids": [first, second], "payload": {"reason": "Role filled"}},
    )
    assert rejected.status_code == 200, rejected.text
    assert len(rejected.json()["succeeded"]) == 2

    async with db() as session:
        app = await session.get(Application, uuid.UUID(first))
        assert app is not None
        assert app.rejection_reason == "Role filled"
        candidate = await session.get(Candidate, app.candidate_id)
        assert candidate is not None and "shortlisted-q4" in candidate.tags

    manager = await login(client, "manager")
    denied = await client.post(
        "/api/v1/applications/bulk-action",
        headers=_auth(manager),
        json={"action": "tag", "ids": [first], "payload": {"add_tags": ["x"]}},
    )
    assert denied.status_code == 403
