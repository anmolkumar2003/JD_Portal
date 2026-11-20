"""application reference number sequence

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-20 00:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS application_reference_seq")


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS application_reference_seq")
