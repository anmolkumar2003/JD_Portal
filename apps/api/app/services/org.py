import base64
import uuid
from collections.abc import Sequence
from typing import Any

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import Department, Location, Organization, User
from app.schemas.org import (
    DepartmentCreate,
    DepartmentPatch,
    LocationCreate,
    LocationPatch,
    OrgSettingsOut,
    OrgSettingsPatch,
    PublicConfigOut,
)
from app.services.compliance import write_audit

MAX_LOGO_BYTES = 256 * 1024
_LOGO_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)
LOGO_KEY = "logo_data_url"


def _not_found(entity: str) -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "not_found", f"{entity} not found")


def _duplicate(entity: str) -> AppError:
    return AppError(status.HTTP_409_CONFLICT, "duplicate_name", f"A {entity} with this name exists")


async def primary_org(session: AsyncSession) -> Organization | None:
    """The portal is single-company: the oldest organization is the company."""
    org: Organization | None = await session.scalar(
        select(Organization).order_by(Organization.created_at).limit(1)
    )
    return org


def org_display_name(org: Organization | None) -> str:
    return org.name if org is not None and org.name else get_settings().org_name


async def public_config(session: AsyncSession) -> PublicConfigOut:
    org = await primary_org(session)
    settings: dict[str, Any] = (org.settings if org is not None else None) or {}
    return PublicConfigOut(
        org_name=org_display_name(org),
        logo_data_url=settings.get(LOGO_KEY),
        features=get_settings().features,
    )


async def _user_org(session: AsyncSession, user: User) -> Organization:
    org = await session.get(Organization, user.org_id)
    if org is None:
        raise _not_found("Organization")
    return org


def _settings_out(org: Organization) -> OrgSettingsOut:
    return OrgSettingsOut(name=org.name, logo_data_url=(org.settings or {}).get(LOGO_KEY))


async def get_org_settings(session: AsyncSession, user: User) -> OrgSettingsOut:
    return _settings_out(await _user_org(session, user))


async def update_org_settings(
    session: AsyncSession, user: User, body: OrgSettingsPatch
) -> OrgSettingsOut:
    org = await _user_org(session, user)
    if body.name is not None and body.name != org.name:
        await write_audit(
            session,
            actor_id=user.id,
            action="org.renamed",
            entity_type="organization",
            entity_id=org.id,
            diff={"from": org.name, "to": body.name},
        )
        org.name = body.name
        await session.commit()
    return _settings_out(org)


def _logo_mime(data: bytes) -> str:
    for signature, mime in _LOGO_SIGNATURES:
        if data.startswith(signature):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    raise AppError(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "invalid_logo",
        "Logo must be a PNG, JPEG or WebP image",
    )


async def set_logo(session: AsyncSession, user: User, data: bytes) -> OrgSettingsOut:
    if len(data) > MAX_LOGO_BYTES:
        raise AppError(
            status.HTTP_413_CONTENT_TOO_LARGE, "logo_too_large", "Logo must be 256 KB or smaller"
        )
    mime = _logo_mime(data)
    org = await _user_org(session, user)
    encoded = base64.b64encode(data).decode("ascii")
    org.settings = {**(org.settings or {}), LOGO_KEY: f"data:{mime};base64,{encoded}"}
    await write_audit(
        session,
        actor_id=user.id,
        action="org.logo_updated",
        entity_type="organization",
        entity_id=org.id,
    )
    await session.commit()
    return _settings_out(org)


async def remove_logo(session: AsyncSession, user: User) -> OrgSettingsOut:
    org = await _user_org(session, user)
    settings = dict(org.settings or {})
    if settings.pop(LOGO_KEY, None) is not None:
        org.settings = settings
        await write_audit(
            session,
            actor_id=user.id,
            action="org.logo_removed",
            entity_type="organization",
            entity_id=org.id,
        )
        await session.commit()
    return _settings_out(org)


# --- Departments and locations (ORG-01) -------------------------------------------------------


async def list_departments(
    session: AsyncSession, user: User, *, include_inactive: bool = False
) -> Sequence[Department]:
    stmt = select(Department).where(Department.org_id == user.org_id)
    if not include_inactive:
        stmt = stmt.where(Department.is_active.is_(True))
    rows = await session.scalars(stmt.order_by(Department.name))
    return rows.all()


async def _ensure_name_free(
    session: AsyncSession,
    model: type[Department] | type[Location],
    org_id: uuid.UUID,
    name: str,
    exclude: uuid.UUID | None = None,
) -> None:
    """Names are unique per organization regardless of case ("SEO" and "seo" clash)."""
    stmt = select(model.id).where(model.org_id == org_id, func.lower(model.name) == name.lower())
    if exclude is not None:
        stmt = stmt.where(model.id != exclude)
    if await session.scalar(stmt) is not None:
        raise _duplicate(model.__name__.lower())


async def _commit_unique(session: AsyncSession, entity: str) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise _duplicate(entity) from exc


async def create_department(
    session: AsyncSession, user: User, body: DepartmentCreate
) -> Department:
    await _ensure_name_free(session, Department, user.org_id, body.name)
    department = Department(org_id=user.org_id, name=body.name)
    session.add(department)
    await session.flush()
    await write_audit(
        session,
        actor_id=user.id,
        action="department.created",
        entity_type="department",
        entity_id=department.id,
        diff={"name": body.name},
    )
    await _commit_unique(session, "department")
    return department


async def update_department(
    session: AsyncSession, user: User, department_id: uuid.UUID, body: DepartmentPatch
) -> Department:
    department = await session.get(Department, department_id)
    if department is None or department.org_id != user.org_id:
        raise _not_found("Department")
    diff: dict[str, Any] = {}
    if body.name is not None and body.name != department.name:
        await _ensure_name_free(session, Department, user.org_id, body.name, department.id)
        diff["name"] = {"from": department.name, "to": body.name}
        department.name = body.name
    if body.is_active is not None and body.is_active != department.is_active:
        diff["is_active"] = body.is_active
        department.is_active = body.is_active
    if diff:
        await write_audit(
            session,
            actor_id=user.id,
            action="department.updated",
            entity_type="department",
            entity_id=department.id,
            diff=diff,
        )
        await _commit_unique(session, "department")
        await session.refresh(department)
    return department


async def list_locations(
    session: AsyncSession, user: User, *, include_inactive: bool = False
) -> Sequence[Location]:
    stmt = select(Location).where(Location.org_id == user.org_id)
    if not include_inactive:
        stmt = stmt.where(Location.is_active.is_(True))
    rows = await session.scalars(stmt.order_by(Location.name))
    return rows.all()


async def create_location(session: AsyncSession, user: User, body: LocationCreate) -> Location:
    await _ensure_name_free(session, Location, user.org_id, body.name)
    location = Location(
        org_id=user.org_id, name=body.name, city=body.city or None, country=body.country or None
    )
    session.add(location)
    await session.flush()
    await write_audit(
        session,
        actor_id=user.id,
        action="location.created",
        entity_type="location",
        entity_id=location.id,
        diff={"name": body.name},
    )
    await _commit_unique(session, "location")
    return location


async def update_location(
    session: AsyncSession, user: User, location_id: uuid.UUID, body: LocationPatch
) -> Location:
    location = await session.get(Location, location_id)
    if location is None or location.org_id != user.org_id:
        raise _not_found("Location")
    changes = body.model_dump(exclude_unset=True)
    if body.name is not None and body.name != location.name:
        await _ensure_name_free(session, Location, user.org_id, body.name, location.id)
    diff: dict[str, Any] = {}
    for field, value in changes.items():
        if value is not None and getattr(location, field) != value:
            diff[field] = value
            setattr(location, field, value)
    if diff:
        await write_audit(
            session,
            actor_id=user.id,
            action="location.updated",
            entity_type="location",
            entity_id=location.id,
            diff=diff,
        )
        await _commit_unique(session, "location")
        await session.refresh(location)
    return location
