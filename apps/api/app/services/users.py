import uuid
from collections.abc import Sequence

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import generate_password, hash_password
from app.models import ActivityLog, User
from app.models.enums import UserRole
from app.schemas.user import UserCreate, UserPatch
from app.services.compliance import write_audit

# Roles that must always keep at least one active account.
_PROTECTED_ROLES = (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)


def _forbidden(message: str) -> AppError:
    return AppError(status.HTTP_403_FORBIDDEN, "forbidden", message)


def _check_can_assign(actor: User, role: UserRole) -> None:
    if role == UserRole.SUPER_ADMIN and actor.role != UserRole.SUPER_ADMIN:
        raise _forbidden("Only a super admin can grant the super_admin role")


async def _get_user(session: AsyncSession, actor: User, user_id: uuid.UUID) -> User:
    user = await session.get(User, user_id)
    if user is None or user.org_id != actor.org_id:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "User not found")
    return user


async def _ensure_email_free(
    session: AsyncSession, email: str, exclude: uuid.UUID | None = None
) -> None:
    stmt = select(User.id).where(User.email == email)
    if exclude is not None:
        stmt = stmt.where(User.id != exclude)
    if await session.scalar(stmt) is not None:
        raise AppError(status.HTTP_409_CONFLICT, "email_taken", "A user with this email exists")


async def _ensure_role_stays_staffed(session: AsyncSession, user: User) -> None:
    """Refuse a change that would leave no active super_admin or hr_admin."""
    if user.role not in _PROTECTED_ROLES or not user.is_active:
        return
    others = await session.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.org_id == user.org_id,
            User.role == user.role,
            User.is_active.is_(True),
            User.id != user.id,
        )
    )
    if not others:
        raise AppError(
            status.HTTP_409_CONFLICT,
            "last_admin",
            f"This is the only active {user.role.value} account; add another one first",
        )


async def list_users(
    session: AsyncSession, actor: User, page: int, page_size: int
) -> tuple[Sequence[User], int]:
    base = select(User).where(User.org_id == actor.org_id)
    total = await session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = await session.scalars(
        base.order_by(User.is_active.desc(), User.full_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return rows.all(), total


async def create_user(session: AsyncSession, actor: User, data: UserCreate) -> tuple[User, str]:
    _check_can_assign(actor, data.role)
    email = data.email.lower()
    await _ensure_email_free(session, email)
    temporary_password = generate_password()
    user = User(
        org_id=actor.org_id,
        email=email,
        full_name=data.full_name,
        role=data.role,
        password_hash=hash_password(temporary_password),
        must_change_password=True,
    )
    session.add(user)
    await session.flush()
    session.add(
        ActivityLog(actor_id=actor.id, action="user.created", meta={"user_id": str(user.id)})
    )
    await write_audit(
        session,
        actor_id=actor.id,
        action="user.created",
        entity_type="user",
        entity_id=user.id,
        diff={"role": data.role.value},
    )
    await session.commit()
    await session.refresh(user)
    return user, temporary_password


async def update_user(
    session: AsyncSession, actor: User, user_id: uuid.UUID, data: UserPatch
) -> User:
    user = await _get_user(session, actor, user_id)
    if user.role == UserRole.SUPER_ADMIN and actor.role != UserRole.SUPER_ADMIN:
        raise _forbidden("Only a super admin can change a super admin account")
    diff: dict[str, object] = {}

    if data.role is not None and data.role != user.role:
        if user.id == actor.id:
            raise _forbidden("You cannot change your own role")
        _check_can_assign(actor, data.role)
        await _ensure_role_stays_staffed(session, user)
        diff["role"] = {"from": user.role.value, "to": data.role.value}
        user.role = data.role

    if data.is_active is not None and data.is_active != user.is_active:
        if user.id == actor.id:
            raise _forbidden("You cannot deactivate your own account")
        if not data.is_active:
            await _ensure_role_stays_staffed(session, user)
        diff["is_active"] = data.is_active
        user.is_active = data.is_active

    if data.email is not None and data.email.lower() != user.email:
        email = data.email.lower()
        await _ensure_email_free(session, email, exclude=user.id)
        diff["email_changed"] = True
        user.email = email

    if data.full_name is not None and data.full_name != user.full_name:
        diff["full_name_changed"] = True
        user.full_name = data.full_name

    if diff:
        await write_audit(
            session,
            actor_id=actor.id,
            action="user.updated",
            entity_type="user",
            entity_id=user.id,
            diff=diff,
        )
        await session.commit()
        await session.refresh(user)
    return user


async def reset_user_password(
    session: AsyncSession, actor: User, user_id: uuid.UUID
) -> tuple[User, str]:
    user = await _get_user(session, actor, user_id)
    if user.role == UserRole.SUPER_ADMIN and actor.role != UserRole.SUPER_ADMIN:
        raise _forbidden("Only a super admin can reset a super admin's password")
    temporary_password = generate_password()
    user.password_hash = hash_password(temporary_password)
    user.must_change_password = True
    user.failed_login_attempts = 0
    user.locked_until = None
    await write_audit(
        session,
        actor_id=actor.id,
        action="user.password_reset_by_admin",
        entity_type="user",
        entity_id=user.id,
    )
    await session.commit()
    await session.refresh(user)
    return user, temporary_password


async def change_role(
    session: AsyncSession, actor: User, user_id: uuid.UUID, role: UserRole
) -> User:
    if role not in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER):
        raise AppError(status.HTTP_400_BAD_REQUEST, "invalid_role", "Role cannot be assigned")
    return await update_user(session, actor, user_id, UserPatch.model_validate({"role": role}))
