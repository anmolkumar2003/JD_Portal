import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

OrgName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
LookupName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool = True


class DepartmentCreate(BaseModel):
    name: LookupName


class DepartmentPatch(BaseModel):
    name: LookupName | None = None
    is_active: bool | None = None


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    city: str | None
    country: str | None
    is_active: bool = True


class LocationCreate(BaseModel):
    name: LookupName
    city: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None
    country: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None


class LocationPatch(BaseModel):
    name: LookupName | None = None
    city: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None
    country: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None
    is_active: bool | None = None


class OrgSettingsOut(BaseModel):
    name: str
    logo_data_url: str | None = None


class OrgSettingsPatch(BaseModel):
    name: OrgName | None = None


class PublicConfigOut(BaseModel):
    """Unauthenticated bootstrap data for the web app: branding and enabled modules."""

    org_name: str
    logo_data_url: str | None
    features: dict[str, bool]
