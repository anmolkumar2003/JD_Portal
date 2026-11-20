import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, TypeVar

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import ColumnElement, Select, exists, false, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import InvalidTokenError, decode_token
from app.models import Job, JobTeam, User
from app.models.enums import TeamRole, UserRole

_bearer = HTTPBearer(auto_error=False)
_RowT = TypeVar("_RowT", bound=tuple[Any, ...])

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)
ORG_WIDE_JOB_ROLES = frozenset({UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER})


def _unauthorized(message: str = "Not authenticated") -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, "unauthorized", message)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None:
        raise _unauthorized()
    try:
        payload = decode_token(credentials.credentials, "access")
        user_id = uuid.UUID(payload["sub"])
    except (InvalidTokenError, ValueError) as exc:
        raise _unauthorized("Invalid or expired token") from exc
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], Awaitable[User]]:
    """Dependency factory: allow only the given roles (AUTH-02)."""
    allowed = frozenset(roles)

    async def checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise AppError(
                status.HTTP_403_FORBIDDEN, "forbidden", "You do not have access to this resource"
            )
        return user

    return checker


AdminUser = Annotated[User, Depends(require_roles(*ADMIN_ROLES))]


# --- Record-level access (AUTH-06) ------------------------------------------------------------


def job_access_clause(user: User) -> ColumnElement[bool]:
    """SQL condition limiting jobs to those the user may see.

    Hiring managers see jobs they manage; interviewers see jobs whose panel they are on
    (via job_team until interview assignments exist). Admins and recruiters see the org.
    """
    if user.role in ORG_WIDE_JOB_ROLES:
        return true()
    if user.role == UserRole.HIRING_MANAGER:
        team_role = TeamRole.MANAGER
    elif user.role == UserRole.INTERVIEWER:
        team_role = TeamRole.INTERVIEWER
    else:
        return false()
    on_team = exists().where(
        JobTeam.job_id == Job.id, JobTeam.user_id == user.id, JobTeam.team_role == team_role
    )
    if user.role == UserRole.HIRING_MANAGER:
        return or_(Job.hiring_manager_id == user.id, on_team)
    return on_team


def scope_jobs_query(user: User, stmt: Select[_RowT]) -> Select[_RowT]:
    """Apply org, soft-delete and record-level filters to a query that selects from jobs."""
    return stmt.where(Job.org_id == user.org_id, Job.deleted_at.is_(None), job_access_clause(user))


async def can_access_job(session: AsyncSession, user: User, job_id: uuid.UUID) -> bool:
    stmt = scope_jobs_query(user, select(Job.id).where(Job.id == job_id))
    return (await session.scalar(stmt)) is not None


async def ensure_job_access(session: AsyncSession, user: User, job_id: uuid.UUID) -> None:
    """Raise 404 (not 403) so users cannot probe for jobs they are not assigned to."""
    if not await can_access_job(session, user, job_id):
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Job not found")
