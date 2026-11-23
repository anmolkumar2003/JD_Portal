import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.models.enums import ParseStatus, pg_enum


class ParsedProfile(BaseModel):
    __tablename__ = "parsed_profiles"
    __table_args__ = (
        Index("ix_parsed_profiles_data", "data", postgresql_using="gin"),
        Index(
            "ix_parsed_profiles_raw_text_trgm",
            "raw_text",
            postgresql_using="gin",
            postgresql_ops={"raw_text": "gin_trgm_ops"},
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    parse_status: Mapped[ParseStatus] = mapped_column(
        pg_enum(ParseStatus, "parse_status"),
        default=ParseStatus.PENDING,
        server_default=ParseStatus.PENDING.value,
        index=True,
    )
    parser_version: Mapped[str | None] = mapped_column(String(50))
    raw_text: Mapped[str | None] = mapped_column(Text)
    # {skills[], education[], experience[], certifications[], links[], summary}
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    total_experience_years: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    confidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    corrected_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)


class AtsCheck(BaseModel):
    __tablename__ = "ats_checks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[int] = mapped_column(Integer, index=True)
    # [{id, label, passed, weight, detail, suggestion}]
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]")
    engine_version: Mapped[str] = mapped_column(String(50))


class MatchResult(BaseModel):
    __tablename__ = "match_results"

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    overall_score: Mapped[int] = mapped_column(Integer, index=True)
    # {skills, experience, education, title, location}
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    matched_skills: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)), default=list, server_default="{}"
    )
    missing_required: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)), default=list, server_default="{}"
    )
    missing_preferred: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)), default=list, server_default="{}"
    )
    extra_skills: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)), default=list, server_default="{}"
    )
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    engine_version: Mapped[str] = mapped_column(String(50))
    inputs_hash: Mapped[str] = mapped_column(String(64))
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
