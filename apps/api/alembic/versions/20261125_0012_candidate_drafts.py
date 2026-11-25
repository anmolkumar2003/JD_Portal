"""candidate drafts: temporary CV staging area for the Add Candidate flow

Revision ID: 20261125_0012
Revises: 20261125_0011
Create Date: 2026-11-25 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261125_0012"
down_revision: str | None = "20261125_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidate_drafts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_candidate_drafts_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_candidate_drafts_created_by_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candidate_drafts")),
    )
    op.create_index(op.f("ix_candidate_drafts_org_id"), "candidate_drafts", ["org_id"])
    op.create_index(op.f("ix_candidate_drafts_created_by"), "candidate_drafts", ["created_by"])
    op.create_index(op.f("ix_candidate_drafts_expires_at"), "candidate_drafts", ["expires_at"])

    op.create_table(
        "candidate_draft_files",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("draft_id", sa.UUID(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("parsed_preview", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["candidate_drafts.id"],
            name=op.f("fk_candidate_draft_files_draft_id_candidate_drafts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candidate_draft_files")),
    )
    op.create_index(
        op.f("ix_candidate_draft_files_draft_id"), "candidate_draft_files", ["draft_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_candidate_draft_files_draft_id"), table_name="candidate_draft_files")
    op.drop_table("candidate_draft_files")
    op.drop_index(op.f("ix_candidate_drafts_expires_at"), table_name="candidate_drafts")
    op.drop_index(op.f("ix_candidate_drafts_created_by"), table_name="candidate_drafts")
    op.drop_index(op.f("ix_candidate_drafts_org_id"), table_name="candidate_drafts")
    op.drop_table("candidate_drafts")
