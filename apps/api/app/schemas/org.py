import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import StageType


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    city: str | None
    country: str | None


class PipelineStageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    order: int
    type: StageType
    is_default: bool
