from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import AuthenticatedUser
from app.core.net import client_ip
from app.core.rate_limit import enforce_rate_limit
from app.core.redis import get_redis
from app.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"
FORGOT_LIMIT_PER_HOUR = 5
LOGIN_LIMIT_PER_15_MIN = 30

Session = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


def _cookie_secure() -> bool:
    settings = get_settings()
    return bool(settings.cookie_secure or settings.app_env == "production")


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
    )


def _token_response(user: User, tokens: auth_service.IssuedTokens) -> TokenResponse:
    return TokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: Session,
    redis: RedisClient,
) -> TokenResponse:
    ip = client_ip(request)
    await enforce_rate_limit(redis, f"ratelimit:login:{ip}", LOGIN_LIMIT_PER_15_MIN, 900)
    user = await auth_service.authenticate(session, body.email, body.password, ip=ip)
    tokens = auth_service.issue_tokens(user)
    _set_refresh_cookie(response, tokens.refresh_token)
    return _token_response(user, tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    session: Session,
    redis: RedisClient,
    refresh_token: RefreshCookie = None,
) -> TokenResponse:
    user, tokens = await auth_service.refresh(session, redis, refresh_token)
    _set_refresh_cookie(response, tokens.refresh_token)
    return _token_response(user, tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(redis: RedisClient, refresh_token: RefreshCookie = None) -> Response:
    await auth_service.logout(redis, refresh_token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(response)
    return response


@router.post(
    "/forgot-password", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED
)
async def forgot_password(
    body: ForgotPasswordRequest, request: Request, session: Session, redis: RedisClient
) -> MessageResponse:
    await enforce_rate_limit(
        redis, f"ratelimit:forgot:{client_ip(request)}", FORGOT_LIMIT_PER_HOUR, 3600
    )
    await auth_service.request_password_reset(session, body.email)
    return MessageResponse(message="If the account exists, a reset email has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, session: Session) -> MessageResponse:
    await auth_service.reset_password(session, body.token, body.new_password)
    return MessageResponse(message="Password updated. You can now log in.")


@router.post("/change-password", response_model=TokenResponse)
async def change_password(
    body: ChangePasswordRequest, user: AuthenticatedUser, session: Session, response: Response
) -> TokenResponse:
    """Also the way out of a forced change after first login or an admin reset. Other sessions
    are signed out; this one gets fresh tokens."""
    updated = await auth_service.change_password(
        session, user, body.current_password, body.new_password
    )
    tokens = auth_service.issue_tokens(updated)
    _set_refresh_cookie(response, tokens.refresh_token)
    return _token_response(updated, tokens)


@router.get("/me", response_model=UserOut)
async def me(user: AuthenticatedUser) -> UserOut:
    return UserOut.model_validate(user)
