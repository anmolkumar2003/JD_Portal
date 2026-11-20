from typing import Any
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Application, Job, PipelineStage
from app.models.enums import StageType
from tests.conftest import login
from tests.test_apply import PDF, _apply, _form


async def test_timeline_includes_apply_and_stage_change(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    stored_objects: dict[str, bytes],
    sent_emails: list[dict[str, Any]],
) -> None:
    apply = await _apply(
        client,
        "senior-backend-engineer",
        data=_form(email="timeline@example.com"),
        file=("cv.pdf", PDF, "application/pdf"),
    )
    assert apply.status_code == 201, apply.text
    reference = apply.json()["reference_no"]
    headers = {"Authorization": f"Bearer {await login(client, 'recruiter')}"}

    async with db() as session:
        application = await session.scalar(
            select(Application).where(Application.reference_no == reference)
        )
        assert application is not None
        candidate_id = str(application.candidate_id)
        app_id = str(application.id)
        job = await session.get(Job, application.job_id)
        assert job is not None
        screening = await session.scalar(
            select(PipelineStage).where(
                PipelineStage.org_id == job.org_id, PipelineStage.type == StageType.SCREENING
            )
        )
        assert screening is not None
        screening_id = str(screening.id)

    await client.patch(
        f"/api/v1/applications/{app_id}/stage",
        headers=headers,
        json={"stage_id": screening_id},
    )

    timeline = await client.get(f"/api/v1/candidates/{candidate_id}/timeline", headers=headers)
    assert timeline.status_code == 200, timeline.text
    events = timeline.json()
    actions = [event["action"] for event in events]
    assert "application.created" in actions
    assert "application.stage_changed" in actions
    stage_event = next(e for e in events if e["action"] == "application.stage_changed")
    assert stage_event["actor"] is not None
    assert stage_event["actor"]["full_name"]
    assert stage_event["meta"]["to_stage"] == "Screening"


async def test_timeline_unknown_candidate_is_404(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
) -> None:
    headers = {"Authorization": f"Bearer {await login(client, 'recruiter')}"}
    response = await client.get(f"/api/v1/candidates/{uuid4()}/timeline", headers=headers)
    assert response.status_code == 404
