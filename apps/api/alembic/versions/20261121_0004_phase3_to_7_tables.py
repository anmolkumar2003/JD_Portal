"""phase 3-7 tables: notes, email, notifications, interviews, offers, audit

Revision ID: 20261121_0004
Revises: 20261120_0003
Create Date: 2026-11-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261121_0004"
down_revision: str | None = "20261120_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    interview_type = sa.Enum(
        "phone", "technical", "managerial", "hr", name="interview_type"
    )
    interview_mode = sa.Enum("video", "onsite", name="interview_mode")
    interview_status = sa.Enum(
        "scheduled", "completed", "cancelled", "rescheduled", name="interview_status"
    )
    recommendation = sa.Enum(
        "strong_no", "no", "mixed", "yes", "strong_yes", name="recommendation"
    )
    requisition_status = sa.Enum(
        "draft", "pending", "approved", "rejected", name="requisition_status"
    )
    offer_status = sa.Enum(
        "draft",
        "pending_approval",
        "approved",
        "sent",
        "accepted",
        "declined",
        "withdrawn",
        name="offer_status",
    )
    interview_type.create(op.get_bind(), checkfirst=True)
    interview_mode.create(op.get_bind(), checkfirst=True)
    interview_status.create(op.get_bind(), checkfirst=True)
    recommendation.create(op.get_bind(), checkfirst=True)
    requisition_status.create(op.get_bind(), checkfirst=True)
    offer_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="SET NULL")),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("mentions", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default="{}"),
    )
    op.create_index("ix_notes_candidate_id", "notes", ["candidate_id"])
    op.create_index("ix_notes_author_id", "notes", ["author_id"])

    op.create_table(
        "email_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("variables", postgresql.ARRAY(sa.String(100)), server_default="{}"),
        sa.Column("trigger_stage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pipeline_stages.id", ondelete="SET NULL")),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
    )
    op.create_index("ix_email_templates_org_id", "email_templates", ["org_id"])
    op.create_index("ix_email_templates_key", "email_templates", ["key"])

    op.create_table(
        "email_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="SET NULL")),
        sa.Column("template_key", sa.String(100)),
        sa.Column("to", sa.String(320), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), server_default="sent"),
        sa.Column("sent_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_email_logs_candidate_id", "email_logs", ["candidate_id"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default="{}"),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_type", "notifications", ["type"])

    op.create_table(
        "scorecard_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("competencies", postgresql.JSONB(), server_default="[]"),
    )

    op.create_table(
        "interviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("round_name", sa.String(200), nullable=False),
        sa.Column("type", interview_type, nullable=False),
        sa.Column("mode", interview_mode, nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_min", sa.Integer(), server_default="60"),
        sa.Column("meeting_link", sa.String(500)),
        sa.Column("location", sa.String(300)),
        sa.Column("status", interview_status, server_default="scheduled"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    op.create_index("ix_interviews_application_id", "interviews", ["application_id"])
    op.create_index("ix_interviews_scheduled_at", "interviews", ["scheduled_at"])

    op.create_table(
        "interview_panel",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("interview_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feedback_submitted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("interview_id", "user_id", name="uq_interview_panel"),
    )

    op.create_table(
        "scorecards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("interview_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("interviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ratings", postgresql.JSONB(), server_default="{}"),
        sa.Column("comments", sa.Text()),
        sa.Column("recommendation", recommendation),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("interview_id", "interviewer_id", name="uq_scorecards_interview_interviewer"),
    )

    op.create_table(
        "requisitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL")),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("headcount", sa.Integer(), server_default="1"),
        sa.Column("budget_min", sa.Numeric(14, 2)),
        sa.Column("budget_max", sa.Numeric(14, 2)),
        sa.Column("justification", sa.Text()),
        sa.Column("status", requisition_status, server_default="draft"),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("designation", sa.String(200), nullable=False),
        sa.Column("ctc_breakdown", postgresql.JSONB(), server_default="{}"),
        sa.Column("joining_date", sa.Date()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("status", offer_status, server_default="draft"),
        sa.Column("approval_chain", postgresql.JSONB(), server_default="[]"),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL")),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("responded_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    op.create_index("ix_offers_application_id", "offers", ["application_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("ip", sa.String(64)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("diff", postgresql.JSONB(), server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_occurred_at", "audit_logs", ["occurred_at"])

    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(200), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ip", sa.String(64)),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
    )
    op.create_index("ix_consent_records_candidate_id", "consent_records", ["candidate_id"])


def downgrade() -> None:
    op.drop_table("consent_records")
    op.drop_table("audit_logs")
    op.drop_table("offers")
    op.drop_table("requisitions")
    op.drop_table("scorecards")
    op.drop_table("interview_panel")
    op.drop_table("interviews")
    op.drop_table("scorecard_templates")
    op.drop_table("notifications")
    op.drop_table("email_logs")
    op.drop_table("email_templates")
    op.drop_table("notes")
    for name in (
        "offer_status",
        "requisition_status",
        "recommendation",
        "interview_status",
        "interview_mode",
        "interview_type",
    ):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
