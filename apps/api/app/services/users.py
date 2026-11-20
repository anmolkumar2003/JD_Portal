import uuid
from collections.abc import Sequence

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import hash_password
from app.models import ActivityLog, User
from app.models.enums import UserRole
from app.schemas.user import UserCreate


def _forbidden(message: str) -> AppError:
    return AppError(status.HTTP_403_FORBIDDEN, "forbidden", message)


def _check_can_assign(actor: User, role: UserRole) -> None:
    if role == UserRole.SUPER_ADMIN and actor.role != UserRole.SUPER_ADMIN:
        raise _forbidden("Only a super admin can grant the super_admin role")


async def list_users(
    session: AsyncSession, actor: User, page: int, page_size: int
) -> tuple[Sequence[User], int]:
    base = select(User).where(User.org_id == actor.org_id)
    total = await session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = await session.scalars(
        base.order_by(User.full_name).offset((page - 1) * page_size).limit(page_size)
    )
    return rows.all(), total


async def create_user(session: AsyncSession, actor: User, data: UserCreate) -> User:
    _check_can_assign(actor, data.role)
    email = data.email.lower()
    if await session.scalar(select(User.id).where(User.email == email)) is not None:
        raise AppError(status.HTTP_409_CONFLICT, "email_taken", "A user with this email exists")

    user = User(
        org_id=actor.org_id,
        email=email,
        full_name=data.full_name,
        role=data.role,
        password_hash=hash_password(data.password),
    )
    session.add(user)
    await session.flush()
    session.add(
        ActivityLog(actor_id=actor.id, action="user.created", meta={"user_id": str(user.id)})
    )
    await session.commit()
    return user


async def change_role(
    session: AsyncSession, actor: User, user_id: uuid.UUID, role: UserRole
) -> User:
    user = await session.get(User, user_id)
    if user is None or user.org_id != actor.org_id:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "User not found")
    if user.id == actor.id:
        raise _forbidden("You cannot change your own role")
    if user.role == UserRole.SUPER_ADMIN and actor.role != UserRole.SUPER_ADMIN:
        raise _forbidden("Only a super admin can change a super admin's role")
    _check_can_assign(actor, role)

    previous = user.role
    user.role = role
    session.add(
        ActivityLog(
            actor_id=actor.id,
            action="user.role_changed",
            meta={"user_id": str(user.id), "from": previous.value, "to": role.value},
        )
    )
    await session.commit()
    await session.refresh(user)
    return user
