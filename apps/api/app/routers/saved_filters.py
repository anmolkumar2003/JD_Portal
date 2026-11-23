import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.schemas.saved_filters import SavedFilterIn, SavedFilterOut
from app.services import saved_filters as saved_filters_service

router = APIRouter(prefix="/api/v1/saved-filters", tags=["saved-filters"])

Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[SavedFilterOut])
async def list_filters(user: CurrentUser, session: Session) -> list[SavedFilterOut]:
    return await saved_filters_service.list_saved(session, user)


@router.post("", response_model=SavedFilterOut, status_code=status.HTTP_201_CREATED)
async def create_filter(body: SavedFilterIn, user: CurrentUser, session: Session) -> SavedFilterOut:
    return await saved_filters_service.create_saved(session, user, body)


@router.put("/{filter_id}", response_model=SavedFilterOut)
async def update_filter(
    filter_id: uuid.UUID, body: SavedFilterIn, user: CurrentUser, session: Session
) -> SavedFilterOut:
    return await saved_filters_service.update_saved(session, user, filter_id, body)


@router.delete("/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_filter(filter_id: uuid.UUID, user: CurrentUser, session: Session) -> Response:
    await saved_filters_service.delete_saved(session, user, filter_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
