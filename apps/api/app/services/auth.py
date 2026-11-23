import inspect
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

from fastapi import status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_token,
    hash_password,
    password_fingerprint,
    password_problems,
    verify_password,
)
from app.models import ActivityLog, Organization, User
from app.services.compliance import write_audit
from app.services.org import org_display_name
from app.workers.tasks import send_email

logger = logging.getLogger(__name__)

REVOKED_KEY = "auth:revoked:{jti}"
# Verified against when the email is unknown, so response time does not reveal which emails exist.
_DUMMY_HASH = hash_password("not-a-real-password")


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    expires_in: int


def _invalid_credentials() -> AppError:
    return AppError(
        status.HTTP_401_UNAUTHORIZED, "invalid_credentials", "Invalid email or password"
    )


def _locked(locked_until: datetime) -> AppError:
    return AppError(
        status.HTTP_423_LOCKED,
        "account_locked",
        "Too many failed login attempts. Try again later.",
        {"locked_until": locked_until.isoformat()},
    )


async def _resolve(value: Any) -> Any:
    # redis-py types commands as sync-or-async; the asyncio client always returns an awaitable.
    return await value if inspect.isawaitable(value) else value


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    user: User | None = await session.scalar(select(User).where(User.email == email.lower()))
    return user


async def authenticate(
    session: AsyncSession, email: str, password: str, ip: str | None = None
) -> User:
    """Check credentials and apply the lockout policy (AUTH-01, AUTH-03)."""
    settings = get_settings()
    user = await get_user_by_email(session, email)
    if user is None:
        verify_password(password, _DUMMY_HASH)
        raise _invalid_credentials()

    now = datetime.now(UTC)
    if user.locked_until is not None and user.locked_until > now:
        raise _locked(user.locked_until)

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_failed_logins:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_login_attempts = 0
            await write_audit(
                session,
                actor_id=user.id,
                action="user.locked",
                entity_type="user",
                entity_id=user.id,
                ip=ip,
            )
            await session.commit()
            logger.warning("account locked", extra={"user_id": str(user.id)})
            raise _locked(user.locked_until)
        await session.commit()
        raise _invalid_credentials()

    if not user.is_active:
        raise _invalid_credentials()

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    await write_audit(
        session,
        actor_id=user.id,
        action="user.login",
        entity_type="user",
        entity_id=user.id,
        ip=ip,
    )
    await session.commit()
    return user


def issue_tokens(user: User) -> IssuedTokens:
    settings = get_settings()
    refresh_token, _ = create_refresh_token(user.id, user.password_hash)
    return IssuedTokens(
        access_token=create_access_token(user.id, user.org_id, user.role.value),
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def _revoke(redis: Redis, payload: dict[str, Any]) -> None:
    jti = payload.get("jti")
    ttl = int(payload["exp"] - datetime.now(UTC).timestamp())
    if jti and ttl > 0:
        await _resolve(redis.set(REVOKED_KEY.format(jti=jti), "1", ex=ttl))


async def refresh(
    session: AsyncSession, redis: Redis, refresh_token: str | None
) -> tuple[User, IssuedTokens]:
    """Exchange a refresh token for a new access token, rotating the refresh token."""
    if not refresh_token:
        raise AppError(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Missing refresh token")
    try:
        payload = decode_token(refresh_token, "refresh")
        user_id = uuid.UUID(payload["sub"])
    except (InvalidTokenError, ValueError) as exc:
        raise AppError(
            status.HTTP_401_UNAUTHORIZED, "unauthorized", "Invalid refresh token"
        ) from exc

    if await _resolve(redis.exists(REVOKED_KEY.format(jti=payload.get("jti", "")))):
        raise AppError(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Refresh token revoked")

    user = await session.get(User, user_id)
    if (
        user is None
        or not user.is_active
        or payload.get("pwd") != password_fingerprint(user.password_hash)
    ):
        raise AppError(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Invalid refresh token")

    await _revoke(redis, payload)
    return user, issue_tokens(user)


async def logout(redis: Redis, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    try:
        payload = decode_token(refresh_token, "refresh")
    except InvalidTokenError:
        return
    await _revoke(redis, payload)


def _weak_password(problems: list[str]) -> AppError:
    return AppError(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "weak_password",
        " ".join(problems),
        {"problems": problems},
    )


def ensure_strong_password(password: str, email: str) -> None:
    problems = password_problems(password, email=email)
    if problems:
        raise _weak_password(problems)


async def request_password_reset(session: AsyncSession, email: str) -> None:
    """Email a reset link if the account exists. Callers always respond the same way."""
    user = await get_user_by_email(session, email)
    if user is None or not user.is_active:
        return
    settings = get_settings()
    minutes = settings.password_reset_expire_minutes
    token = create_reset_token(user.id, user.password_hash)
    link = f"{settings.web_base_url.rstrip('/')}/reset-password?token={quote(token)}"
    portal = f"{org_display_name(await session.get(Organization, user.org_id))} HR portal"
    body = (
        f"Hi {user.full_name},\n\n"
        f"We received a request to reset your {portal} password.\n\n"
        f"Open this link within {minutes} minutes to choose a new password (single use):\n\n"
        f"{link}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )
    send_email.delay(user.email, f"Reset your {portal} password", body)


async def reset_password(session: AsyncSession, token: str, new_password: str) -> None:
    invalid = AppError(
        status.HTTP_400_BAD_REQUEST, "invalid_token", "Reset link is invalid or expired"
    )
    try:
        payload = decode_token(token, "reset")
        user_id = uuid.UUID(payload["sub"])
    except (InvalidTokenError, ValueError) as exc:
        raise invalid from exc

    user = await session.get(User, user_id)
    if user is None or payload.get("pwd") != password_fingerprint(user.password_hash):
        raise invalid
    ensure_strong_password(new_password, user.email)

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.failed_login_attempts = 0
    user.locked_until = None
    session.add(ActivityLog(actor_id=user.id, action="user.password_reset", meta={}))
    await write_audit(
        session,
        actor_id=user.id,
        action="user.password_reset",
        entity_type="user",
        entity_id=user.id,
    )
    await session.commit()


async def change_password(
    session: AsyncSession, user: User, current_password: str, new_password: str
) -> User:
    if not verify_password(current_password, user.password_hash):
        raise AppError(
            status.HTTP_400_BAD_REQUEST, "invalid_password", "Current password is incorrect"
        )
    if current_password == new_password:
        raise _weak_password(["Choose a password different from the current one."])
    ensure_strong_password(new_password, user.email)
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    await write_audit(
        session,
        actor_id=user.id,
        action="user.password_changed",
        entity_type="user",
        entity_id=user.id,
    )
    await session.commit()
    await session.refresh(user)
    return user
