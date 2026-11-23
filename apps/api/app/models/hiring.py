"""Requisitions and offers (REQ, OFFER)."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.models.enums import pg_enum


class RequisitionStatus(enum.StrEnum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class OfferStatus(enum.StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"


class Requisition(BaseModel):
    __tablename__ = "requisitions"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), index=True
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    headcount: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    budget_min: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    budget_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    justification: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RequisitionStatus] = mapped_column(
        pg_enum(RequisitionStatus, "requisition_status"),
        default=RequisitionStatus.DRAFT,
        server_default=RequisitionStatus.DRAFT.value,
        index=True,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Offer(BaseModel):
    __tablename__ = "offers"

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    designation: Mapped[str] = mapped_column(String(200))
    ctc_breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    joining_date: Mapped[date | None] = mapped_column(Date)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[OfferStatus] = mapped_column(
        pg_enum(OfferStatus, "offer_status"),
        default=OfferStatus.DRAFT,
        server_default=OfferStatus.DRAFT.value,
        index=True,
    )
    approval_chain: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
