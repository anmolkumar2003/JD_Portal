from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import ActivityLog, Application, Job, PipelineStage
from app.models.enums import ApplicationStatus, StageType
from tests.conftest import login
from tests.test_apply import BACKEND, _apply, _form

pytestmark = pytest.mark.usefixtures("db", "sent_emails", "stored_objects")


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _seed_application(client: AsyncClient) -> dict[str, Any]:
    response = await _apply(client, data=_form("pipeline@example.com"))
    assert response.status_code == 201, response.text
    return response.json()


async def test_list_applications_and_hm_scope(client: AsyncClient) -> None:
    await _seed_application(client)
    recruiter = await login(client, "recruiter")
    listed = await client.get("/api/v1/applications", headers=_auth(recruiter))
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["total"] >= 1
    assert body["items"][0]["email"] == "pipeline@example.com"
    assert body["items"][0]["stage"]["type"] == "applied"

    manager = await login(client, "manager")
    hm_list = await client.get("/api/v1/applications", headers=_auth(manager))
    assert hm_list.status_code == 200
    # Seeded jobs are owned by the hiring manager, so their applicants are visible.
    assert hm_list.json()["total"] >= 1

    interviewer = await login(client, "interviewer")
    # Interviewer is on the seeded backend job panel, so that applicant is visible.
    panel = await client.get("/api/v1/applications", headers=_auth(interviewer))
    assert panel.status_code == 200
    assert panel.json()["total"] >= 1


async def test_get_application_detail(client: AsyncClient) -> None:
    await _seed_application(client)
    token = await login(client, "recruiter")
    listed = await client.get("/api/v1/applications", headers=_auth(token))
    app_id = listed.json()["items"][0]["id"]

    detail = await client.get(f"/api/v1/applications/{app_id}", headers=_auth(token))
    assert detail.status_code == 200, detail.text
    data = detail.json()
    assert data["candidate"]["email"] == "pipeline@example.com"
    assert data["documents"]
    assert data["parsed_profile"] is not None
    assert data["match_result"] is None


async def test_job_board_and_stage_move_with_reject(
    client: AsyncClient, db: async_sessionmaker[AsyncSession]
) -> None:
    await _seed_application(client)
    token = await login(client, "recruiter")

    async with db() as session:
        job = await session.scalar(select(Job).where(Job.slug == BACKEND))
        assert job is not None
        stages = {
            s.type: s
            for s in await session.scalars(
                select(PipelineStage).where(PipelineStage.org_id == job.org_id)
            )
        }
        job_id = str(job.id)
        screening_id = str(stages[StageType.SCREENING].id)
        rejected_id = str(stages[StageType.REJECTED].id)

    board = await client.get(f"/api/v1/jobs/{job_id}/board", headers=_auth(token))
    assert board.status_code == 200, board.text
    columns = {col["stage"]["type"]: col for col in board.json()["stages"]}
    assert columns["applied"]["count"] >= 1
    application_id = columns["applied"]["cards"][0]["id"]

    moved = await client.patch(
        f"/api/v1/applications/{application_id}/stage",
        headers=_auth(token),
        json={"stage_id": screening_id},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["stage"]["type"] == "screening"

    reject_missing = await client.patch(
        f"/api/v1/applications/{application_id}/stage",
        headers=_auth(token),
        json={"stage_id": rejected_id},
    )
    assert reject_missing.status_code == 400
    assert reject_missing.json()["error"]["code"] == "rejection_reason_required"

    rejected = await client.patch(
        f"/api/v1/applications/{application_id}/stage",
        headers=_auth(token),
        json={"stage_id": rejected_id, "reason": "Not enough Python experience"},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == ApplicationStatus.REJECTED.value
    assert rejected.json()["rejection_reason"] == "Not enough Python experience"

    async with db() as session:
        application = await session.get(Application, application_id)
        assert application is not None
        assert application.status == ApplicationStatus.REJECTED
        logs = list(
            await session.scalars(
                select(ActivityLog)
                .where(ActivityLog.application_id == application.id)
                .order_by(ActivityLog.occurred_at)
            )
        )
        actions = [log.action for log in logs]
        assert "application.created" in actions
        assert actions.count("application.stage_changed") >= 2
        reject_log = next(
            log
            for log in logs
            if log.action == "application.stage_changed"
            and log.meta.get("to_stage_type") == "rejected"
        )
        assert reject_log.meta.get("reason") == "Not enough Python experience"
        assert reject_log.actor_id is not None

    candidate_id = rejected.json()["candidate"]["id"]
    timeline = await client.get(
        f"/api/v1/candidates/{candidate_id}/timeline", headers=_auth(token)
    )
    assert timeline.status_code == 200, timeline.text
    entries = timeline.json()
    assert any(e["action"] == "application.created" for e in entries)
    assert any(
        e["action"] == "application.stage_changed" and e["meta"].get("reason") for e in entries
    )


async def test_hm_cannot_move_stage(client: AsyncClient) -> None:
    await _seed_application(client)
    recruiter = await login(client, "recruiter")
    listed = await client.get("/api/v1/applications", headers=_auth(recruiter))
    app_id = listed.json()["items"][0]["id"]
    stage_id = listed.json()["items"][0]["stage"]["id"]

    manager = await login(client, "manager")
    response = await client.patch(
        f"/api/v1/applications/{app_id}/stage",
        headers=_auth(manager),
        json={"stage_id": stage_id},
    )
    assert response.status_code == 403


async def test_search_filter(client: AsyncClient) -> None:
    await _seed_application(client)
    token = await login(client, "recruiter")
    hit = await client.get("/api/v1/applications", headers=_auth(token), params={"q": "pipeline"})
    assert hit.status_code == 200
    assert hit.json()["total"] >= 1
    miss = await client.get("/api/v1/applications", headers=_auth(token), params={"q": "zzzz-none"})
    assert miss.status_code == 200
    assert miss.json()["total"] == 0
