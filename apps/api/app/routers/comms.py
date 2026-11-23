import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.comms import (
    EmailLogOut,
    EmailPreviewIn,
    EmailPreviewOut,
    EmailSendIn,
    EmailTemplateIn,
    EmailTemplateOut,
    NotificationOut,
)
from app.services import emails as emails_service
from app.services import notifications as notifications_service

router = APIRouter(prefix="/api/v1", tags=["comms"])
Session = Annotated[AsyncSession, Depends(get_db)]
Editor = Annotated[
    User,
    Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER)),
]


@router.get("/email-templates", response_model=list[EmailTemplateOut])
async def list_templates(user: CurrentUser, session: Session) -> list[EmailTemplateOut]:
    return await emails_service.list_templates(session, user)


@router.post("/email-templates", response_model=EmailTemplateOut)
async def create_template(
    body: EmailTemplateIn, user: Editor, session: Session
) -> EmailTemplateOut:
    return await emails_service.upsert_template(session, user, body)


@router.post("/emails/preview", response_model=EmailPreviewOut)
async def preview_email(body: EmailPreviewIn, user: CurrentUser) -> EmailPreviewOut:
    return emails_service.preview(body)


@router.post("/emails/send", response_model=EmailLogOut)
async def send_email(body: EmailSendIn, user: Editor, session: Session) -> EmailLogOut:
    return await emails_service.send_candidate_email(session, user, body)


@router.get("/candidates/{candidate_id}/emails", response_model=list[EmailLogOut])
async def candidate_emails(
    candidate_id: uuid.UUID, user: CurrentUser, session: Session
) -> list[EmailLogOut]:
    return await emails_service.list_candidate_emails(session, user, candidate_id)


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    user: CurrentUser,
    session: Session,
    unread_only: Annotated[bool, Query()] = False,
) -> list[NotificationOut]:
    return await notifications_service.list_notifications(session, user, unread_only=unread_only)


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
async def read_notification(
    notification_id: uuid.UUID, user: CurrentUser, session: Session
) -> NotificationOut:
    return await notifications_service.mark_read(session, user, notification_id)


@router.post("/notifications/read-all")
async def read_all(user: CurrentUser, session: Session) -> dict[str, int]:
    return {"updated": await notifications_service.mark_all_read(session, user)}
