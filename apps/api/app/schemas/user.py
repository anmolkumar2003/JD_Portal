import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.models.enums import UserRole

# Roles an admin can hand out from Settings > Users.
AssignableRole = Literal[UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER]
FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    must_change_password: bool = False
    last_login_at: datetime | None
    created_at: datetime | None = None


class UserCreate(BaseModel):
    email: EmailStr
    full_name: FullName
    role: AssignableRole


class UserPatch(BaseModel):
    email: EmailStr | None = None
    full_name: FullName | None = None
    role: AssignableRole | None = None
    is_active: bool | None = None


class UserWithTemporaryPassword(BaseModel):
    """Returned once when an admin creates or resets a user; the password is never stored."""

    user: UserOut
    temporary_password: str


class UserRoleUpdate(BaseModel):
    role: AssignableRole


class UserList(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int = Field(ge=1)
