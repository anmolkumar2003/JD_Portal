import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Sequence,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseModel, SoftDeleteMixin
from app.models.enums import (
    ApplicationStatus,
    CandidateSource,
    DocumentType,
    VirusScanStatus,
    pg_enum,
)


class Candidate(BaseModel, SoftDeleteMixin):
    __tablename__ = "candidates"
    __table_args__ = (
        UniqueConstraint("org_id", "email", name="uq_candidates_org_id_email"),
        Index("ix_candidates_tags", "tags", postgresql_using="gin"),
        Index(
            "ix_candidates_first_name_trgm",
            "first_name",
            postgresql_using="gin",
            postgresql_ops={"first_name": "gin_trgm_ops"},
        ),
        Index(
            "ix_candidates_last_name_trgm",
            "last_name",
            postgresql_using="gin",
            postgresql_ops={"last_name": "gin_trgm_ops"},
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(40), index=True)
    current_location: Mapped[str | None] = mapped_column(String(200))
    current_company: Mapped[str | None] = mapped_column(String(200))
    current_title: Mapped[str | None] = mapped_column(String(200))
    total_experience_years: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    current_ctc: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    expected_ctc: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    notice_period_days: Mapped[int | None] = mapped_column(Integer)
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    portfolio_url: Mapped[str | None] = mapped_column(String(500))
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), index=True
    )
    source: Mapped[CandidateSource] = mapped_column(
        pg_enum(CandidateSource, "candidate_source"),
        default=CandidateSource.CAREER_SITE,
        server_default=CandidateSource.CAREER_SITE.value,
        index=True,
    )
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list, server_default="{}")
    is_talent_pool: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[str | None] = mapped_column(String(20))


APPLICATION_REFERENCE_SEQ = Sequence("application_reference_seq", metadata=Base.metadata)


class Application(BaseModel):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_applications_candidate_id_job_id"),
        Index("ix_applications_job_id_stage_id", "job_id", "stage_id"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    stage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipeline_stages.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        pg_enum(ApplicationStatus, "application_status"),
        default=ApplicationStatus.ACTIVE,
        server_default=ApplicationStatus.ACTIVE.value,
        index=True,
    )
    reference_no: Mapped[str] = mapped_column(String(32), unique=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    cover_letter: Mapped[str | None] = mapped_column(Text)
    answers: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    stage_entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    assigned_recruiter_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    is_shortlisted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    overall_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))


class Document(BaseModel):
    __tablename__ = "documents"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    type: Mapped[DocumentType] = mapped_column(pg_enum(DocumentType, "document_type"))
    file_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    checksum: Mapped[str] = mapped_column(String(64))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    virus_scan_status: Mapped[VirusScanStatus] = mapped_column(
        pg_enum(VirusScanStatus, "virus_scan_status"),
        default=VirusScanStatus.PENDING,
        server_default=VirusScanStatus.PENDING.value,
    )
