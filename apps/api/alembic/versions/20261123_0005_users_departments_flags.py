"""must_change_password, active flags on departments/locations, candidate department

Revision ID: 20261123_0005
Revises: 20261121_0004
Create Date: 2026-11-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261123_0005"
down_revision: str | None = "20261121_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "departments",
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "locations",
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column("candidates", sa.Column("department_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_candidates_department_id_departments",
        "candidates",
        "departments",
        ["department_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_candidates_department_id", "candidates", ["department_id"])


def downgrade() -> None:
    op.drop_index("ix_candidates_department_id", table_name="candidates")
    op.drop_constraint(
        "fk_candidates_department_id_departments", "candidates", type_="foreignkey"
    )
    op.drop_column("candidates", "department_id")
    op.drop_column("locations", "is_active")
    op.drop_column("departments", "is_active")
    op.drop_column("users", "must_change_password")
