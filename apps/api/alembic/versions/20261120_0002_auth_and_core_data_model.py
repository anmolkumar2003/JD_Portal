"""auth and core data model

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-20 13:39:19.725364

organizations and users (AUTH-01, ORG-02) plus the core tables from SPEC Part 7:
departments, locations, pipeline_stages, jobs, job_requirements, job_team, candidates,
applications, documents, parsed_profiles, ats_checks, match_results, activity_logs.
jobs.requisition_id has no FK until the requisitions table exists.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# create_table creates these implicitly; drop_table does not remove them.
ENUM_TYPES = (
    "user_role",
    "work_mode",
    "employment_type",
    "job_status",
    "team_role",
    "stage_type",
    "candidate_source",
    "application_status",
    "document_type",
    "virus_scan_status",
    "parse_status",
)


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column(
            "settings", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
    )
    op.create_table(
        "candidates",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("current_location", sa.String(length=200), nullable=True),
        sa.Column("current_company", sa.String(length=200), nullable=True),
        sa.Column("current_title", sa.String(length=200), nullable=True),
        sa.Column("total_experience_years", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("current_ctc", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("expected_ctc", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("notice_period_days", sa.Integer(), nullable=True),
        sa.Column("linkedin_url", sa.String(length=500), nullable=True),
        sa.Column("portfolio_url", sa.String(length=500), nullable=True),
        sa.Column(
            "source",
            sa.Enum(
                "career_site", "referral", "linkedin", "agency", "manual", name="candidate_source"
            ),
            server_default="career_site",
            nullable=False,
        ),
        sa.Column(
            "tags", postgresql.ARRAY(sa.String(length=50)), server_default="{}", nullable=False
        ),
        sa.Column("is_talent_pool", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_version", sa.String(length=20), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_candidates_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candidates")),
        sa.UniqueConstraint("org_id", "email", name="uq_candidates_org_id_email"),
    )
    op.create_index(
        "ix_candidates_first_name_trgm",
        "candidates",
        ["first_name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"first_name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_candidates_last_name_trgm",
        "candidates",
        ["last_name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"last_name": "gin_trgm_ops"},
    )
    op.create_index(op.f("ix_candidates_org_id"), "candidates", ["org_id"], unique=False)
    op.create_index(op.f("ix_candidates_phone"), "candidates", ["phone"], unique=False)
    op.create_index(op.f("ix_candidates_source"), "candidates", ["source"], unique=False)
    op.create_index(
        "ix_candidates_tags", "candidates", ["tags"], unique=False, postgresql_using="gin"
    )
    op.create_table(
        "locations",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_locations_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_locations")),
        sa.UniqueConstraint("org_id", "name", name="uq_locations_org_id_name"),
    )
    op.create_index(op.f("ix_locations_org_id"), "locations", ["org_id"], unique=False)
    op.create_table(
        "pipeline_stages",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "applied",
                "screening",
                "interview",
                "offer",
                "hired",
                "rejected",
                "custom",
                name="stage_type",
            ),
            nullable=False,
        ),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_pipeline_stages_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pipeline_stages")),
        sa.UniqueConstraint("org_id", "name", name="uq_pipeline_stages_org_id_name"),
        sa.UniqueConstraint("org_id", "order", name="uq_pipeline_stages_org_id_order"),
    )
    op.create_index(op.f("ix_pipeline_stages_org_id"), "pipeline_stages", ["org_id"], unique=False)
    op.create_table(
        "users",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "super_admin",
                "hr_admin",
                "recruiter",
                "hiring_manager",
                "interviewer",
                name="user_role",
            ),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mfa_secret", sa.String(length=255), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_users_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_org_id"), "users", ["org_id"], unique=False)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.create_table(
        "departments",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("head_user_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["head_user_id"],
            ["users.id"],
            name=op.f("fk_departments_head_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_departments_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_departments")),
        sa.UniqueConstraint("org_id", "name", name="uq_departments_org_id_name"),
    )
    op.create_index(
        op.f("ix_departments_head_user_id"), "departments", ["head_user_id"], unique=False
    )
    op.create_index(op.f("ix_departments_org_id"), "departments", ["org_id"], unique=False)
    op.create_table(
        "jobs",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("requisition_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("location_id", sa.UUID(), nullable=True),
        sa.Column(
            "work_mode", sa.Enum("onsite", "hybrid", "remote", name="work_mode"), nullable=False
        ),
        sa.Column(
            "employment_type",
            sa.Enum("full_time", "part_time", "contract", "internship", name="employment_type"),
            nullable=False,
        ),
        sa.Column("level", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("responsibilities", sa.Text(), nullable=True),
        sa.Column("qualifications", sa.Text(), nullable=True),
        sa.Column("salary_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("salary_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("salary_currency", sa.String(length=3), nullable=True),
        sa.Column("openings", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "open", "on_hold", "closed", "filled", name="job_status"),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hiring_manager_id", sa.UUID(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "screening_questions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_jobs_created_by_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name=op.f("fk_jobs_department_id_departments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["hiring_manager_id"],
            ["users.id"],
            name=op.f("fk_jobs_hiring_manager_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name=op.f("fk_jobs_location_id_locations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_jobs_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
        sa.UniqueConstraint("slug", name=op.f("uq_jobs_slug")),
    )
    op.create_index(op.f("ix_jobs_created_by"), "jobs", ["created_by"], unique=False)
    op.create_index(op.f("ix_jobs_department_id"), "jobs", ["department_id"], unique=False)
    op.create_index(op.f("ix_jobs_hiring_manager_id"), "jobs", ["hiring_manager_id"], unique=False)
    op.create_index(op.f("ix_jobs_location_id"), "jobs", ["location_id"], unique=False)
    op.create_index(op.f("ix_jobs_org_id"), "jobs", ["org_id"], unique=False)
    op.create_index(op.f("ix_jobs_requisition_id"), "jobs", ["requisition_id"], unique=False)
    op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)
    op.create_table(
        "applications",
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("stage_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "rejected", "withdrawn", "hired", name="application_status"),
            server_default="active",
            nullable=False,
        ),
        sa.Column("reference_no", sa.String(length=32), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("cover_letter", sa.Text(), nullable=True),
        sa.Column(
            "answers", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "stage_entered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("assigned_recruiter_id", sa.UUID(), nullable=True),
        sa.Column("is_shortlisted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("overall_rating", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assigned_recruiter_id"],
            ["users.id"],
            name=op.f("fk_applications_assigned_recruiter_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name=op.f("fk_applications_candidate_id_candidates"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_applications_job_id_jobs"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["stage_id"],
            ["pipeline_stages.id"],
            name=op.f("fk_applications_stage_id_pipeline_stages"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
        sa.UniqueConstraint("candidate_id", "job_id", name="uq_applications_candidate_id_job_id"),
        sa.UniqueConstraint("reference_no", name=op.f("uq_applications_reference_no")),
    )
    op.create_index(
        op.f("ix_applications_applied_at"), "applications", ["applied_at"], unique=False
    )
    op.create_index(
        op.f("ix_applications_assigned_recruiter_id"),
        "applications",
        ["assigned_recruiter_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_applications_candidate_id"), "applications", ["candidate_id"], unique=False
    )
    op.create_index(op.f("ix_applications_job_id"), "applications", ["job_id"], unique=False)
    op.create_index(
        "ix_applications_job_id_stage_id", "applications", ["job_id", "stage_id"], unique=False
    )
    op.create_index(op.f("ix_applications_stage_id"), "applications", ["stage_id"], unique=False)
    op.create_index(op.f("ix_applications_status"), "applications", ["status"], unique=False)
    op.create_table(
        "job_requirements",
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column(
            "required_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "preferred_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("min_experience", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("max_experience", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("education_level", sa.String(length=100), nullable=True),
        sa.Column(
            "certifications",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("weights_override", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name=op.f("fk_job_requirements_job_id_jobs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_requirements")),
    )
    op.create_index(op.f("ix_job_requirements_job_id"), "job_requirements", ["job_id"], unique=True)
    op.create_table(
        "job_team",
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "team_role",
            sa.Enum("recruiter", "interviewer", "manager", name="team_role"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_job_team_job_id_jobs"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_job_team_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_team")),
        sa.UniqueConstraint("job_id", "user_id", "team_role", name="uq_job_team_job_user_role"),
    )
    op.create_index(op.f("ix_job_team_job_id"), "job_team", ["job_id"], unique=False)
    op.create_index(op.f("ix_job_team_user_id"), "job_team", ["user_id"], unique=False)
    op.create_table(
        "activity_logs",
        sa.Column("candidate_id", sa.UUID(), nullable=True),
        sa.Column("application_id", sa.UUID(), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column(
            "metadata", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_activity_logs_actor_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_activity_logs_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name=op.f("fk_activity_logs_candidate_id_candidates"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_logs")),
    )
    op.create_index(op.f("ix_activity_logs_action"), "activity_logs", ["action"], unique=False)
    op.create_index(op.f("ix_activity_logs_actor_id"), "activity_logs", ["actor_id"], unique=False)
    op.create_index(
        op.f("ix_activity_logs_application_id"), "activity_logs", ["application_id"], unique=False
    )
    op.create_index(
        op.f("ix_activity_logs_candidate_id"), "activity_logs", ["candidate_id"], unique=False
    )
    op.create_index(
        op.f("ix_activity_logs_occurred_at"), "activity_logs", ["occurred_at"], unique=False
    )
    op.create_table(
        "documents",
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=True),
        sa.Column(
            "type",
            sa.Enum("cv", "cover_letter", "offer", "other", name="document_type"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "virus_scan_status",
            sa.Enum("pending", "clean", "infected", "failed", name="virus_scan_status"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_documents_application_id_applications"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name=op.f("fk_documents_candidate_id_candidates"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_documents_storage_key")),
    )
    op.create_index(
        op.f("ix_documents_application_id"), "documents", ["application_id"], unique=False
    )
    op.create_index(op.f("ix_documents_candidate_id"), "documents", ["candidate_id"], unique=False)
    op.create_table(
        "match_results",
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column(
            "breakdown",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "matched_skills",
            postgresql.ARRAY(sa.String(length=100)),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "missing_required",
            postgresql.ARRAY(sa.String(length=100)),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "missing_preferred",
            postgresql.ARRAY(sa.String(length=100)),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "extra_skills",
            postgresql.ARRAY(sa.String(length=100)),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "explanation",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("engine_version", sa.String(length=50), nullable=False),
        sa.Column("inputs_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_match_results_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_match_results")),
    )
    op.create_index(
        op.f("ix_match_results_application_id"), "match_results", ["application_id"], unique=False
    )
    op.create_index(
        op.f("ix_match_results_overall_score"), "match_results", ["overall_score"], unique=False
    )
    op.create_table(
        "ats_checks",
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column(
            "checks", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column("engine_version", sa.String(length=50), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_ats_checks_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ats_checks")),
    )
    op.create_index(op.f("ix_ats_checks_document_id"), "ats_checks", ["document_id"], unique=False)
    op.create_table(
        "parsed_profiles",
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column(
            "parse_status",
            sa.Enum("pending", "processing", "done", "failed", name="parse_status"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("parser_version", sa.String(length=50), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column(
            "data", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("total_experience_years", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column(
            "confidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("corrected_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name=op.f("fk_parsed_profiles_candidate_id_candidates"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_parsed_profiles_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_parsed_profiles")),
    )
    op.create_index(
        op.f("ix_parsed_profiles_candidate_id"), "parsed_profiles", ["candidate_id"], unique=False
    )
    op.create_index(
        "ix_parsed_profiles_data", "parsed_profiles", ["data"], unique=False, postgresql_using="gin"
    )
    op.create_index(
        op.f("ix_parsed_profiles_document_id"), "parsed_profiles", ["document_id"], unique=False
    )
    op.create_index(
        op.f("ix_parsed_profiles_parse_status"), "parsed_profiles", ["parse_status"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_parsed_profiles_parse_status"), table_name="parsed_profiles")
    op.drop_index(op.f("ix_parsed_profiles_document_id"), table_name="parsed_profiles")
    op.drop_index("ix_parsed_profiles_data", table_name="parsed_profiles", postgresql_using="gin")
    op.drop_index(op.f("ix_parsed_profiles_candidate_id"), table_name="parsed_profiles")
    op.drop_table("parsed_profiles")
    op.drop_index(op.f("ix_ats_checks_document_id"), table_name="ats_checks")
    op.drop_table("ats_checks")
    op.drop_index(op.f("ix_match_results_overall_score"), table_name="match_results")
    op.drop_index(op.f("ix_match_results_application_id"), table_name="match_results")
    op.drop_table("match_results")
    op.drop_index(op.f("ix_documents_candidate_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_application_id"), table_name="documents")
    op.drop_table("documents")
    op.drop_index(op.f("ix_activity_logs_occurred_at"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_candidate_id"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_application_id"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_actor_id"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_action"), table_name="activity_logs")
    op.drop_table("activity_logs")
    op.drop_index(op.f("ix_job_team_user_id"), table_name="job_team")
    op.drop_index(op.f("ix_job_team_job_id"), table_name="job_team")
    op.drop_table("job_team")
    op.drop_index(op.f("ix_job_requirements_job_id"), table_name="job_requirements")
    op.drop_table("job_requirements")
    op.drop_index(op.f("ix_applications_status"), table_name="applications")
    op.drop_index(op.f("ix_applications_stage_id"), table_name="applications")
    op.drop_index("ix_applications_job_id_stage_id", table_name="applications")
    op.drop_index(op.f("ix_applications_job_id"), table_name="applications")
    op.drop_index(op.f("ix_applications_candidate_id"), table_name="applications")
    op.drop_index(op.f("ix_applications_assigned_recruiter_id"), table_name="applications")
    op.drop_index(op.f("ix_applications_applied_at"), table_name="applications")
    op.drop_table("applications")
    op.drop_index(op.f("ix_jobs_status"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_requisition_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_org_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_location_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_hiring_manager_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_department_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_created_by"), table_name="jobs")
    op.drop_table("jobs")
    op.drop_index(op.f("ix_departments_org_id"), table_name="departments")
    op.drop_index(op.f("ix_departments_head_user_id"), table_name="departments")
    op.drop_table("departments")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_org_id"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_pipeline_stages_org_id"), table_name="pipeline_stages")
    op.drop_table("pipeline_stages")
    op.drop_index(op.f("ix_locations_org_id"), table_name="locations")
    op.drop_table("locations")
    op.drop_index("ix_candidates_tags", table_name="candidates", postgresql_using="gin")
    op.drop_index(op.f("ix_candidates_source"), table_name="candidates")
    op.drop_index(op.f("ix_candidates_phone"), table_name="candidates")
    op.drop_index(op.f("ix_candidates_org_id"), table_name="candidates")
    op.drop_index(
        "ix_candidates_last_name_trgm",
        table_name="candidates",
        postgresql_using="gin",
        postgresql_ops={"last_name": "gin_trgm_ops"},
    )
    op.drop_index(
        "ix_candidates_first_name_trgm",
        table_name="candidates",
        postgresql_using="gin",
        postgresql_ops={"first_name": "gin_trgm_ops"},
    )
    op.drop_table("candidates")
    op.drop_table("organizations")
    for enum_name in ENUM_TYPES:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
