import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import AdminUser, CurrentUser
from app.schemas.candidate_actions import UserRef
from app.schemas.user import (
    UserCreate,
    UserList,
    UserOut,
    UserPatch,
    UserRoleUpdate,
    UserWithTemporaryPassword,
)
from app.services import candidate_actions as actions_service
from app.services import users as users_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])

Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=UserList)
async def list_users(
    actor: AdminUser,
    session: Session,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> UserList:
    items, total = await users_service.list_users(session, actor, page, page_size)
    return UserList(
        items=[UserOut.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/lookup", response_model=list[UserRef])
async def lookup_users(user: CurrentUser, session: Session) -> list[UserRef]:
    """Active org users (id, name, role only) for @mention pickers."""
    return await actions_service.lookup_users(session, user)


@router.post("", response_model=UserWithTemporaryPassword, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate, actor: AdminUser, session: Session
) -> UserWithTemporaryPassword:
    """New users get a one-time temporary password and must change it on first login."""
    user, password = await users_service.create_user(session, actor, body)
    return UserWithTemporaryPassword(user=UserOut.model_validate(user), temporary_password=password)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID, body: UserPatch, actor: AdminUser, session: Session
) -> UserOut:
    user = await users_service.update_user(session, actor, user_id, body)
    return UserOut.model_validate(user)


@router.post("/{user_id}/reset-password", response_model=UserWithTemporaryPassword)
async def reset_user_password(
    user_id: uuid.UUID, actor: AdminUser, session: Session
) -> UserWithTemporaryPassword:
    user, password = await users_service.reset_user_password(session, actor, user_id)
    return UserWithTemporaryPassword(user=UserOut.model_validate(user), temporary_password=password)


@router.patch("/{user_id}/role", response_model=UserOut)
async def change_role(
    user_id: uuid.UUID, body: UserRoleUpdate, actor: AdminUser, session: Session
) -> UserOut:
    user = await users_service.change_role(session, actor, user_id, body.role)
    return UserOut.model_validate(user)
