import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import AdminUser
from app.schemas.user import UserCreate, UserList, UserOut, UserRoleUpdate
from app.services import users as users_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])

Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=UserList)
async def list_users(
    actor: AdminUser,
    session: Session,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> UserList:
    items, total = await users_service.list_users(session, actor, page, page_size)
    return UserList(
        items=[UserOut.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, actor: AdminUser, session: Session) -> UserOut:
    user = await users_service.create_user(session, actor, body)
    return UserOut.model_validate(user)


@router.patch("/{user_id}/role", response_model=UserOut)
async def change_role(
    user_id: uuid.UUID, body: UserRoleUpdate, actor: AdminUser, session: Session
) -> UserOut:
    user = await users_service.change_role(session, actor, user_id, body.role)
    return UserOut.model_validate(user)
