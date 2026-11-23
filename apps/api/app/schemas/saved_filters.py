from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

FilterName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class SavedFilterIn(BaseModel):
    name: FilterName
    filters: dict[str, Any] = Field(default_factory=dict)


class SavedFilterOut(BaseModel):
    id: UUID
    name: str
    filters: dict[str, Any]
