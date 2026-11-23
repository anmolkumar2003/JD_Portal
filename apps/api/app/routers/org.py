import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import AdminUser, CurrentUser
from app.schemas.org import (
    DepartmentCreate,
    DepartmentOut,
    DepartmentPatch,
    LocationCreate,
    LocationOut,
    LocationPatch,
    OrgSettingsOut,
    OrgSettingsPatch,
    PublicConfigOut,
)
from app.services import org as org_service

router = APIRouter(prefix="/api/v1", tags=["org"])

Session = Annotated[AsyncSession, Depends(get_db)]
IncludeInactive = Annotated[bool, Query()]


@router.get("/config", response_model=PublicConfigOut)
async def public_config(session: Session) -> PublicConfigOut:
    """Branding and enabled modules. Public so the sign-in page can show the company name."""
    return await org_service.public_config(session)


@router.get("/org/settings", response_model=OrgSettingsOut)
async def get_org_settings(user: AdminUser, session: Session) -> OrgSettingsOut:
    return await org_service.get_org_settings(session, user)


@router.patch("/org/settings", response_model=OrgSettingsOut)
async def update_org_settings(
    body: OrgSettingsPatch, user: AdminUser, session: Session
) -> OrgSettingsOut:
    return await org_service.update_org_settings(session, user, body)


@router.put("/org/logo", response_model=OrgSettingsOut)
async def upload_logo(
    user: AdminUser, session: Session, file: Annotated[UploadFile, File()]
) -> OrgSettingsOut:
    data = await file.read(org_service.MAX_LOGO_BYTES + 1)
    return await org_service.set_logo(session, user, data)


@router.delete("/org/logo", response_model=OrgSettingsOut)
async def delete_logo(user: AdminUser, session: Session) -> OrgSettingsOut:
    return await org_service.remove_logo(session, user)


@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(
    user: CurrentUser, session: Session, include_inactive: IncludeInactive = False
) -> list[DepartmentOut]:
    rows = await org_service.list_departments(session, user, include_inactive=include_inactive)
    return [DepartmentOut.model_validate(d) for d in rows]


@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
async def create_department(
    body: DepartmentCreate, user: AdminUser, session: Session
) -> DepartmentOut:
    return DepartmentOut.model_validate(await org_service.create_department(session, user, body))


@router.patch("/departments/{department_id}", response_model=DepartmentOut)
async def update_department(
    department_id: uuid.UUID, body: DepartmentPatch, user: AdminUser, session: Session
) -> DepartmentOut:
    department = await org_service.update_department(session, user, department_id, body)
    return DepartmentOut.model_validate(department)


@router.get("/locations", response_model=list[LocationOut])
async def list_locations(
    user: CurrentUser, session: Session, include_inactive: IncludeInactive = False
) -> list[LocationOut]:
    rows = await org_service.list_locations(session, user, include_inactive=include_inactive)
    return [LocationOut.model_validate(loc) for loc in rows]


@router.post("/locations", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
async def create_location(body: LocationCreate, user: AdminUser, session: Session) -> LocationOut:
    return LocationOut.model_validate(await org_service.create_location(session, user, body))


@router.patch("/locations/{location_id}", response_model=LocationOut)
async def update_location(
    location_id: uuid.UUID, body: LocationPatch, user: AdminUser, session: Session
) -> LocationOut:
    location = await org_service.update_location(session, user, location_id, body)
    return LocationOut.model_validate(location)
