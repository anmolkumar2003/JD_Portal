from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import ActivityLog, Application, Job, PipelineStage, User
from app.models.enums import StageType
from tests.conftest import login
from tests.test_apply import PDF, _apply, _form

BACKEND = "senior-backend-engineer"


async def _headers(client: AsyncClient, handle: str = "recruiter") -> dict[str, str]:
    return {"Authorization": f"Bearer {await login(client, handle)}"}


async def test_board_shows_applied_card_and_stage_move_logs_actor(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    stored_objects: dict[str, bytes],
    sent_emails: list[dict[str, Any]],
) -> None:
    apply = await _apply(
        client,
        BACKEND,
        data=_form(email="board@example.com"),
        file=("cv.pdf", PDF, "application/pdf"),
    )
    assert apply.status_code == 201, apply.text
    reference = apply.json()["reference_no"]
    headers = await _headers(client)

    async with db() as session:
        job = await session.scalar(select(Job).where(Job.slug == BACKEND))
        assert job is not None
        job_id = str(job.id)
        application = await session.scalar(
            select(Application).where(Application.reference_no == reference)
        )
        assert application is not None
        app_id = str(application.id)
        application_uuid = application.id
        screening = await session.scalar(
            select(PipelineStage).where(
                PipelineStage.org_id == job.org_id, PipelineStage.type == StageType.SCREENING
            )
        )
        assert screening is not None
        screening_id = str(screening.id)
        recruiter = await session.scalar(
            select(User).where(User.email == "recruiter@acme.example.com")
        )
        assert recruiter is not None
        recruiter_id = str(recruiter.id)

    board = await client.get(f"/api/v1/jobs/{job_id}/board", headers=headers)
    assert board.status_code == 200, board.text
    payload = board.json()
    assert payload["job_id"] == job_id
    applied_col = next(col for col in payload["stages"] if col["stage"]["type"] == "applied")
    assert applied_col["count"] >= 1
    assert any(card["reference_no"] == reference for card in applied_col["cards"])

    moved = await client.patch(
        f"/api/v1/applications/{app_id}/stage",
        headers=headers,
        json={"stage_id": screening_id},
    )
    assert moved.status_code == 200, moved.text

    board2 = await client.get(f"/api/v1/jobs/{job_id}/board", headers=headers)
    assert board2.status_code == 200
    screening_col = next(
        col for col in board2.json()["stages"] if col["stage"]["type"] == "screening"
    )
    assert any(card["id"] == app_id for card in screening_col["cards"])

    async with db() as session:
        log = await session.scalar(
            select(ActivityLog)
            .where(
                ActivityLog.application_id == application_uuid,
                ActivityLog.action == "application.stage_changed",
            )
            .order_by(ActivityLog.occurred_at.desc())
        )
        assert log is not None
        assert str(log.actor_id) == recruiter_id
        assert log.meta.get("to_stage") == "Screening"
