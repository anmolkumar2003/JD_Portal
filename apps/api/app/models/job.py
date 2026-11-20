import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, SoftDeleteMixin
from app.models.enums import EmploymentType, JobStatus, TeamRole, WorkMode, pg_enum


class Job(BaseModel, SoftDeleteMixin):
    __tablename__ = "jobs"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    # The requisitions table arrives in a later slice; the FK is added then.
    requisition_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), index=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), index=True
    )
    work_mode: Mapped[WorkMode] = mapped_column(pg_enum(WorkMode, "work_mode"))
    employment_type: Mapped[EmploymentType] = mapped_column(
        pg_enum(EmploymentType, "employment_type")
    )
    level: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    responsibilities: Mapped[str | None] = mapped_column(Text)
    qualifications: Mapped[str | None] = mapped_column(Text)
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    openings: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    status: Mapped[JobStatus] = mapped_column(
        pg_enum(JobStatus, "job_status"),
        default=JobStatus.DRAFT,
        server_default=JobStatus.DRAFT.value,
        index=True,
    )
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hiring_manager_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    screening_questions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )


class JobRequirement(BaseModel):
    __tablename__ = "job_requirements"

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, index=True
    )
    # [{"name": str, "weight": float}]
    required_skills: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    preferred_skills: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    min_experience: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    max_experience: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    education_level: Mapped[str | None] = mapped_column(String(100))
    certifications: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    weights_override: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class JobTeam(BaseModel):
    __tablename__ = "job_team"
    __table_args__ = (
        UniqueConstraint("job_id", "user_id", "team_role", name="uq_job_team_job_user_role"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    team_role: Mapped[TeamRole] = mapped_column(pg_enum(TeamRole, "team_role"))
