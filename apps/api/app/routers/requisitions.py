import uuid
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_roles
from app.models import User
from app.models.enums import UserRole
from app.services import requisitions as requisitions_service

router = APIRouter(prefix="/api/v1/requisitions", tags=["requisitions"])
Session = Annotated[AsyncSession, Depends(get_db)]
Requester = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.HR_ADMIN,
            UserRole.RECRUITER,
            UserRole.HIRING_MANAGER,
        )
    ),
]


class RequisitionCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    department_id: uuid.UUID | None = None
    headcount: int = Field(default=1, ge=1, le=100)
    budget_min: Decimal | None = None
    budget_max: Decimal | None = None
    justification: str | None = None


@router.get("")
async def list_requisitions(user: CurrentUser, session: Session) -> list[dict[str, Any]]:
    return await requisitions_service.list_requisitions(session, user)


@router.post("")
async def create_requisition(
    body: RequisitionCreate, user: Requester, session: Session
) -> dict[str, Any]:
    return await requisitions_service.create_requisition(
        session,
        user,
        title=body.title,
        department_id=body.department_id,
        headcount=body.headcount,
        budget_min=body.budget_min,
        budget_max=body.budget_max,
        justification=body.justification,
    )


@router.post("/{req_id}/submit")
async def submit_requisition(req_id: uuid.UUID, user: Requester, session: Session) -> dict[str, Any]:
    return await requisitions_service.submit_requisition(session, user, req_id)


@router.post("/{req_id}/approve")
async def approve_requisition(
    req_id: uuid.UUID, user: Requester, session: Session
) -> dict[str, Any]:
    return await requisitions_service.approve_requisition(session, user, req_id)


@router.post("/{req_id}/convert-to-job")
async def convert_to_job(req_id: uuid.UUID, user: Requester, session: Session) -> dict[str, Any]:
    return await requisitions_service.convert_to_job(session, user, req_id)
