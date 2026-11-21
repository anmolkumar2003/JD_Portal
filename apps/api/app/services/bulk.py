"""Bulk application actions (CAND-06)."""

from __future__ import annotations

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Application, Candidate, User
from app.schemas.application import StagePatch
from app.schemas.comms import BulkActionIn, BulkActionOut
from app.services import applications as applications_service


async def bulk_action(session: AsyncSession, user: User, body: BulkActionIn) -> BulkActionOut:
    updated = 0
    for app_id in body.application_ids:
        if body.action == "move_stage":
            if body.stage_id is None:
                raise AppError(
                    status.HTTP_400_BAD_REQUEST, "stage_required", "stage_id is required"
                )
            await applications_service.move_stage(
                session, user, app_id, StagePatch(stage_id=body.stage_id, reason=body.reason)
            )
            updated += 1
        elif body.action == "reject":
            stages = await applications_service.list_pipeline_stages(session, user)
            rejected = next((s for s in stages if s.type.value == "rejected"), None)
            if rejected is None:
                raise AppError(status.HTTP_409_CONFLICT, "no_rejected_stage", "No Rejected stage")
            await applications_service.move_stage(
                session,
                user,
                app_id,
                StagePatch(stage_id=rejected.id, reason=body.reason or "Rejected"),
            )
            updated += 1
        elif body.action == "tag":
            app = await session.get(Application, app_id)
            if app is None:
                continue
            candidate = await session.get(Candidate, app.candidate_id)
            if candidate is None or candidate.org_id != user.org_id:
                continue
            tags = list(dict.fromkeys([*(candidate.tags or []), *body.tags]))
            candidate.tags = tags
            updated += 1
        elif body.action == "shortlist":
            app = await session.get(Application, app_id)
            if app is None:
                continue
            app.is_shortlisted = True
            updated += 1
    await session.commit()
    return BulkActionOut(updated=updated)
