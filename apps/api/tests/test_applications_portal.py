from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Application, Job, PipelineStage
from app.models.enums import StageType
from tests.conftest import login
from tests.test_apply import PDF, _apply, _form

BACKEND = "senior-backend-engineer"


async def _auth_headers(client: AsyncClient, handle: str = "recruiter") -> dict[str, str]:
    token = await login(client, handle)
    return {"Authorization": f"Bearer {token}"}


async def _create_application(
    client: AsyncClient,
    *,
    email: str = "portal.cand@example.com",
    slug: str = BACKEND,
) -> str:
    response = await _apply(
        client, slug, data=_form(email=email), file=("cv.pdf", PDF, "application/pdf")
    )
    assert response.status_code == 201, response.text
    return response.json()["reference_no"]


async def test_list_applications_filters_and_pagination(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    stored_objects: dict[str, bytes],
    sent_emails: list[dict[str, Any]],
) -> None:
    await _create_application(client, email="one@example.com")
    await _create_application(client, email="two@example.com", slug="frontend-engineer")
    headers = await _auth_headers(client)

    listed = await client.get("/api/v1/applications", headers=headers)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["total"] >= 2
    assert len(body["items"]) >= 2

    async with db() as session:
        job = await session.scalar(select(Job).where(Job.slug == BACKEND))
        assert job is not None
        job_id = str(job.id)

    filtered = await client.get(
        "/api/v1/applications",
        headers=headers,
        params={"job_id": job_id, "q": "one@example.com"},
    )
    assert filtered.status_code == 200, filtered.text
    data = filtered.json()
    assert data["total"] == 1
    assert data["items"][0]["candidate"]["email"] == "one@example.com"
    assert data["items"][0]["job"]["id"] == job_id
    assert data["items"][0]["source"] == "career_site"


async def test_get_application_detail_and_stage_change(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    stored_objects: dict[str, bytes],
    sent_emails: list[dict[str, Any]],
) -> None:
    reference = await _create_application(client, email="move@example.com")
    headers = await _auth_headers(client)

    async with db() as session:
        application = await session.scalar(
            select(Application).where(Application.reference_no == reference)
        )
        assert application is not None
        app_id = str(application.id)
        job = await session.get(Job, application.job_id)
        assert job is not None
        screening = await session.scalar(
            select(PipelineStage).where(
                PipelineStage.org_id == job.org_id,
                PipelineStage.type == StageType.SCREENING,
            )
        )
        assert screening is not None
        screening_id = str(screening.id)

    detail = await client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["reference_no"] == reference
    assert payload["stage"]["type"] == "applied"
    assert payload["match_result"] is None
    assert payload["parsed_profile"] is not None
    assert payload["documents"]

    moved = await client.patch(
        f"/api/v1/applications/{app_id}/stage",
        headers=headers,
        json={"stage_id": screening_id},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["stage"]["type"] == "screening"


async def test_reject_requires_reason(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    stored_objects: dict[str, bytes],
    sent_emails: list[dict[str, Any]],
) -> None:
    reference = await _create_application(client, email="reject@example.com")
    headers = await _auth_headers(client)

    async with db() as session:
        application = await session.scalar(
            select(Application).where(Application.reference_no == reference)
        )
        assert application is not None
        app_id = str(application.id)
        job = await session.get(Job, application.job_id)
        assert job is not None
        rejected = await session.scalar(
            select(PipelineStage).where(
                PipelineStage.org_id == job.org_id, PipelineStage.type == StageType.REJECTED
            )
        )
        assert rejected is not None
        rejected_id = str(rejected.id)

    missing = await client.patch(
        f"/api/v1/applications/{app_id}/stage",
        headers=headers,
        json={"stage_id": rejected_id},
    )
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "rejection_reason_required"

    ok = await client.patch(
        f"/api/v1/applications/{app_id}/stage",
        headers=headers,
        json={"stage_id": rejected_id, "rejection_reason": "Not enough backend experience"},
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["status"] == "rejected"
    assert body["rejection_reason"] == "Not enough backend experience"
    assert body["stage"]["type"] == "rejected"


async def test_hiring_manager_only_sees_managed_jobs(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    stored_objects: dict[str, bytes],
    sent_emails: list[dict[str, Any]],
) -> None:
    # Manager is hiring_manager on seeded backend + frontend jobs.
    await _create_application(client, email="hm@example.com", slug=BACKEND)
    headers = await _auth_headers(client, "manager")
    listed = await client.get("/api/v1/applications", headers=headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] >= 1

    interviewer = await _auth_headers(client, "interviewer")
    as_interviewer = await client.get("/api/v1/applications", headers=interviewer)
    assert as_interviewer.status_code == 200
    # Seeded interviewer is only on the backend job team.
    for item in as_interviewer.json()["items"]:
        assert item["job"]["name"] == "Senior Backend Engineer"
