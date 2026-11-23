"""Named saved filter sets for the candidates list."""

from __future__ import annotations

import uuid

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import User
from app.models.saved_filters import SavedFilter
from app.schemas.saved_filters import SavedFilterIn, SavedFilterOut


def _out(row: SavedFilter) -> SavedFilterOut:
    return SavedFilterOut(id=row.id, name=row.name, filters=dict(row.filters or {}))


async def list_saved(session: AsyncSession, user: User) -> list[SavedFilterOut]:
    rows = list(
        await session.scalars(
            select(SavedFilter).where(SavedFilter.user_id == user.id).order_by(SavedFilter.name)
        )
    )
    return [_out(r) for r in rows]


async def create_saved(session: AsyncSession, user: User, body: SavedFilterIn) -> SavedFilterOut:
    row = SavedFilter(org_id=user.org_id, user_id=user.id, name=body.name, filters=body.filters)
    session.add(row)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            status.HTTP_409_CONFLICT, "duplicate_name", "You already have a filter with that name"
        ) from exc
    await session.refresh(row)
    return _out(row)


async def update_saved(
    session: AsyncSession, user: User, filter_id: uuid.UUID, body: SavedFilterIn
) -> SavedFilterOut:
    row = await session.get(SavedFilter, filter_id)
    if row is None or row.user_id != user.id:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Saved filter not found")
    row.name = body.name
    row.filters = body.filters
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            status.HTTP_409_CONFLICT, "duplicate_name", "You already have a filter with that name"
        ) from exc
    await session.refresh(row)
    return _out(row)


async def delete_saved(session: AsyncSession, user: User, filter_id: uuid.UUID) -> None:
    row = await session.get(SavedFilter, filter_id)
    if row is None or row.user_id != user.id:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Saved filter not found")
    await session.delete(row)
    await session.commit()
