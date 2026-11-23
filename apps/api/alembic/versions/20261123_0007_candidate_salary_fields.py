"""candidate salary fields

Adds currency, unit (pa/pm) and negotiable flag for current/expected/offered CTC.

Revision ID: 20261123_0007
Revises: 20261123_0006
Create Date: 2026-11-23 08:24:52.198869
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261123_0007"
down_revision: str | None = "20261123_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

salary_unit = sa.Enum("pa", "pm", name="salary_unit")


def upgrade() -> None:
    salary_unit.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "candidates",
        sa.Column(
            "current_ctc_currency", sa.String(length=3), server_default="INR", nullable=False
        ),
    )
    op.add_column(
        "candidates",
        sa.Column("current_ctc_unit", salary_unit, server_default="pa", nullable=False),
    )
    op.add_column(
        "candidates",
        sa.Column("current_ctc_negotiable", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "candidates",
        sa.Column(
            "expected_ctc_currency", sa.String(length=3), server_default="INR", nullable=False
        ),
    )
    op.add_column(
        "candidates",
        sa.Column("expected_ctc_unit", salary_unit, server_default="pa", nullable=False),
    )
    op.add_column(
        "candidates",
        sa.Column("expected_ctc_negotiable", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "candidates", sa.Column("offered_ctc", sa.Numeric(precision=14, scale=2), nullable=True)
    )
    op.add_column(
        "candidates",
        sa.Column(
            "offered_ctc_currency", sa.String(length=3), server_default="INR", nullable=False
        ),
    )
    op.add_column(
        "candidates",
        sa.Column("offered_ctc_unit", salary_unit, server_default="pa", nullable=False),
    )
    op.add_column(
        "candidates",
        sa.Column("offered_ctc_negotiable", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("candidates", "offered_ctc_negotiable")
    op.drop_column("candidates", "offered_ctc_unit")
    op.drop_column("candidates", "offered_ctc_currency")
    op.drop_column("candidates", "offered_ctc")
    op.drop_column("candidates", "expected_ctc_negotiable")
    op.drop_column("candidates", "expected_ctc_unit")
    op.drop_column("candidates", "expected_ctc_currency")
    op.drop_column("candidates", "current_ctc_negotiable")
    op.drop_column("candidates", "current_ctc_unit")
    op.drop_column("candidates", "current_ctc_currency")
    salary_unit.drop(op.get_bind(), checkfirst=True)
