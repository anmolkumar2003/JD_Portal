"""search and filter indexes

Revision ID: 20261123_0010
Revises: 20261123_0009
Create Date: 2026-11-23 15:30:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261123_0010"
down_revision: str | None = "20261123_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index("ix_candidates_current_location", "candidates", ["current_location"])
    op.create_index(
        "ix_candidates_total_experience_years", "candidates", ["total_experience_years"]
    )
    op.create_index("ix_candidates_notice_period_days", "candidates", ["notice_period_days"])
    op.create_index(
        "ix_candidates_expected_ctc_lookup",
        "candidates",
        ["expected_ctc_currency", "expected_ctc_unit", "expected_ctc"],
    )
    op.create_index("ix_applications_overall_rating", "applications", ["overall_rating"])
    op.create_index("ix_ats_checks_score", "ats_checks", ["score"])
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_candidates_current_company_trgm "
        "ON candidates USING gin (current_company gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_candidates_current_title_trgm "
        "ON candidates USING gin (current_title gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_parsed_profiles_raw_text_trgm "
        "ON parsed_profiles USING gin (raw_text gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notes_body_trgm "
        "ON notes USING gin (body gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_notes_body_trgm")
    op.execute("DROP INDEX IF EXISTS ix_parsed_profiles_raw_text_trgm")
    op.execute("DROP INDEX IF EXISTS ix_candidates_current_title_trgm")
    op.execute("DROP INDEX IF EXISTS ix_candidates_current_company_trgm")
    op.drop_index("ix_ats_checks_score", table_name="ats_checks")
    op.drop_index("ix_applications_overall_rating", table_name="applications")
    op.drop_index("ix_candidates_expected_ctc_lookup", table_name="candidates")
    op.drop_index("ix_candidates_notice_period_days", table_name="candidates")
    op.drop_index("ix_candidates_total_experience_years", table_name="candidates")
    op.drop_index("ix_candidates_current_location", table_name="candidates")
