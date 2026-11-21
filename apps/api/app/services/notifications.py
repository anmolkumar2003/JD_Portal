"""In-app notifications (COMM-03)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Notification, User
from app.schemas.comms import NotificationOut


async def list_notifications(
    session: AsyncSession, user: User, *, unread_only: bool = False
) -> list[NotificationOut]:
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(50)
    rows = await session.scalars(stmt)
    return [NotificationOut.model_validate(r) for r in rows]


async def mark_read(session: AsyncSession, user: User, notification_id: uuid.UUID) -> NotificationOut:
    row = await session.get(Notification, notification_id)
    if row is None or row.user_id != user.id:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Notification not found")
    row.read_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(row)
    return NotificationOut.model_validate(row)


async def mark_all_read(session: AsyncSession, user: User) -> int:
    result = await session.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )
    await session.commit()
    return int(result.rowcount or 0)
