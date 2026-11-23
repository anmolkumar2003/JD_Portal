import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_roles
from app.models import User
from app.models.enums import UserRole
from app.services import offers as offers_service

router = APIRouter(prefix="/api/v1/offers", tags=["offers"])
Session = Annotated[AsyncSession, Depends(get_db)]
Editor = Annotated[
    User,
    Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER)),
]
Approver = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.HR_ADMIN,
            UserRole.HIRING_MANAGER,
        )
    ),
]


class OfferCreate(BaseModel):
    application_id: uuid.UUID
    designation: str = Field(min_length=1, max_length=200)
    ctc_breakdown: dict[str, Any] = Field(default_factory=dict)
    joining_date: date | None = None
    approval_chain: list[dict[str, Any]] = Field(default_factory=list)


@router.post("")
async def create_offer(body: OfferCreate, user: Editor, session: Session) -> dict[str, Any]:
    return await offers_service.create_offer(
        session,
        user,
        application_id=body.application_id,
        designation=body.designation,
        ctc_breakdown=body.ctc_breakdown,
        joining_date=body.joining_date,
        approval_chain=body.approval_chain,
    )


@router.post("/{offer_id}/submit")
async def submit_offer(offer_id: uuid.UUID, user: Editor, session: Session) -> dict[str, Any]:
    return await offers_service.submit_for_approval(session, user, offer_id)


@router.post("/{offer_id}/approve")
async def approve_offer(offer_id: uuid.UUID, user: Approver, session: Session) -> dict[str, Any]:
    return await offers_service.approve_offer(session, user, offer_id)


@router.post("/{offer_id}/send")
async def send_offer(offer_id: uuid.UUID, user: Editor, session: Session) -> dict[str, Any]:
    return await offers_service.send_offer(session, user, offer_id)


@router.post("/{offer_id}/accept")
async def accept_offer(offer_id: uuid.UUID, user: Editor, session: Session) -> dict[str, Any]:
    return await offers_service.accept_offer(session, user, offer_id)
