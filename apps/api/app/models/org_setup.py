import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.models.enums import StageType, pg_enum


class Department(BaseModel):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_departments_org_id_name"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    head_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Location(BaseModel):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_locations_org_id_name"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class PipelineStage(BaseModel):
    __tablename__ = "pipeline_stages"
    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_pipeline_stages_org_id_name"),
        UniqueConstraint("org_id", "order", name="uq_pipeline_stages_org_id_order"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    order: Mapped[int] = mapped_column(Integer)
    type: Mapped[StageType] = mapped_column(pg_enum(StageType, "stage_type"))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
