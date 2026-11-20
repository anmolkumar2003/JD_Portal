import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.models.enums import EmploymentType, JobStatus, TeamRole, UserRole, WorkMode

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]
SkillName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Currency = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Z]{3}$")
]
Experience = Annotated[Decimal, Field(ge=0, le=50, max_digits=4, decimal_places=1)]
Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


def _check_range(low: Decimal | None, high: Decimal | None, label: str) -> None:
    if low is not None and high is not None and low > high:
        raise ValueError(f"{label} minimum must not exceed the maximum")


# --- Requirements (JOB-02) --------------------------------------------------------------------


class Skill(BaseModel):
    name: SkillName
    weight: float = Field(default=1.0, gt=0, le=1)


class RequirementsIn(BaseModel):
    required_skills: list[Skill] = Field(default_factory=list, max_length=50)
    preferred_skills: list[Skill] = Field(default_factory=list, max_length=50)
    min_experience: Experience | None = None
    max_experience: Experience | None = None
    education_level: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None
    ) = None

    @model_validator(mode="after")
    def _validate(self) -> Self:
        _check_range(self.min_experience, self.max_experience, "Experience")
        required = {s.name.casefold() for s in self.required_skills}
        if len(required) != len(self.required_skills):
            raise ValueError("Required skills contain duplicates")
        preferred = [s.name.casefold() for s in self.preferred_skills]
        if len(set(preferred)) != len(preferred):
            raise ValueError("Preferred skills contain duplicates")
        if required & set(preferred):
            raise ValueError("A skill cannot be both required and preferred")
        return self


class RequirementsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    required_skills: list[Skill]
    preferred_skills: list[Skill]
    min_experience: Decimal | None
    max_experience: Decimal | None
    education_level: str | None


# --- Jobs (JOB-01, JOB-03) --------------------------------------------------------------------


class JobFields(BaseModel):
    title: Title
    department_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    work_mode: WorkMode
    employment_type: EmploymentType
    level: Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)] | None = None
    description: str = Field(default="", max_length=20_000)
    responsibilities: str | None = Field(default=None, max_length=20_000)
    qualifications: str | None = Field(default=None, max_length=20_000)
    salary_min: Money | None = None
    salary_max: Money | None = None
    salary_currency: Currency | None = None
    openings: int = Field(default=1, ge=1, le=1000)
    closes_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def _validate_salary(self) -> Self:
        _check_range(self.salary_min, self.salary_max, "Salary")
        return self


class JobCreate(JobFields):
    requirements: RequirementsIn | None = None


class JobUpdate(BaseModel):
    """PATCH body: only the fields that are sent are changed."""

    title: Title | None = None
    department_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    work_mode: WorkMode | None = None
    employment_type: EmploymentType | None = None
    level: Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)] | None = None
    description: str | None = Field(default=None, max_length=20_000)
    responsibilities: str | None = Field(default=None, max_length=20_000)
    qualifications: str | None = Field(default=None, max_length=20_000)
    salary_min: Money | None = None
    salary_max: Money | None = None
    salary_currency: Currency | None = None
    openings: int | None = Field(default=None, ge=1, le=1000)
    closes_at: AwareDatetime | None = None


class JobFilters(BaseModel):
    status: JobStatus | None = None
    department_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    q: str | None = Field(default=None, max_length=200)


class NamedRef(BaseModel):
    id: uuid.UUID
    name: str


class TeamMemberIn(BaseModel):
    user_id: uuid.UUID
    team_role: TeamRole


class TeamIn(BaseModel):
    hiring_manager_id: uuid.UUID | None = None
    members: list[TeamMemberIn] = Field(default_factory=list, max_length=50)


class TeamMemberOut(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    role: UserRole
    team_role: TeamRole


class JobListItem(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    status: JobStatus
    department: NamedRef | None
    location: NamedRef | None
    work_mode: WorkMode
    employment_type: EmploymentType
    openings: int
    applicants_count: int
    published_at: datetime | None
    closes_at: datetime | None
    created_at: datetime


class JobOut(JobListItem):
    level: str | None
    description: str
    responsibilities: str | None
    qualifications: str | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    salary_currency: str | None
    updated_at: datetime
    hiring_manager: NamedRef | None
    requirements: RequirementsOut | None
    team: list[TeamMemberOut]


# --- Public careers site (JOB-04) -------------------------------------------------------------


class PublicJobListItem(BaseModel):
    slug: str
    title: str
    department: NamedRef | None
    location: NamedRef | None
    work_mode: WorkMode
    employment_type: EmploymentType
    level: str | None
    published_at: datetime | None
    closes_at: datetime | None


class PublicJobOut(PublicJobListItem):
    description: str
    responsibilities: str | None
    qualifications: str | None
    openings: int
    required_skills: list[str]
    preferred_skills: list[str]
    min_experience: Decimal | None
    education_level: str | None
