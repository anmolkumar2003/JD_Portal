import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import AdminUser, CurrentUser
from app.services import compliance as compliance_service

router = APIRouter(prefix="/api/v1", tags=["admin"])
Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("/candidates/{candidate_id}/export")
async def export_candidate(
    candidate_id: uuid.UUID, user: CurrentUser, session: Session
) -> dict[str, Any]:
    return await compliance_service.export_candidate(session, user, candidate_id)


@router.post("/candidates/{candidate_id}/anonymize")
async def anonymize_candidate(
    candidate_id: uuid.UUID, user: AdminUser, session: Session
) -> dict[str, str]:
    return await compliance_service.anonymize_candidate(session, user, candidate_id)


@router.get("/audit-logs")
async def audit_logs(user: AdminUser, session: Session) -> list[dict[str, Any]]:
    return await compliance_service.list_audit_logs(session, user)
