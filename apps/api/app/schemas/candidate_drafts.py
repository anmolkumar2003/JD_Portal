"""Schemas for the Add Candidate draft area (B1) and committing a draft (B5)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import BudgetStatus, CandidateSource
from app.schemas.application import CvParseOut
from app.schemas.salary import SalaryIn

MAX_COMMIT_ROWS = 50


class DraftOut(BaseModel):
    id: UUID
    expires_at: datetime


class DraftFileUploadOut(CvParseOut):
    """Parsed fields (same shape as /parse-cv) plus the ids needed to commit later."""

    draft_id: UUID
    draft_file_id: UUID


class DraftDeleteOut(BaseModel):
    id: UUID
    deleted: bool = True
    files_deleted: int


class CommitMode(StrEnum):
    COMPLETE_ONLY = "complete_only"
    ALL = "all"


class DraftCommitRowIn(BaseModel):
    """One candidate to save. Everything is optional here on purpose: required-field rules are
    enforced per row by the service, so `complete_only` can save the valid rows and report the
    rest instead of rejecting the whole request."""

    draft_file_id: UUID | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    job_id: UUID | None = None
    department_id: UUID | None = None
    current_location: str | None = None
    current_company: str | None = None
    current_title: str | None = None
    total_experience_years: Decimal | None = None
    notice_period_days: int | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    source: CandidateSource = CandidateSource.MANUAL
    tags: list[str] = Field(default_factory=list)
    current_ctc: SalaryIn | None = None
    expected_ctc: SalaryIn | None = None
    offered_ctc: SalaryIn | None = None


class DraftCommitIn(BaseModel):
    mode: CommitMode = CommitMode.ALL
    rows: list[DraftCommitRowIn] = Field(min_length=1, max_length=MAX_COMMIT_ROWS)


class RowIssue(BaseModel):
    field: str
    message: str


class RowStatus(StrEnum):
    SAVED = "saved"
    INCOMPLETE = "incomplete"
    FAILED = "failed"


class DraftCommitRowOut(BaseModel):
    index: int
    draft_file_id: UUID | None = None
    status: RowStatus
    issues: list[RowIssue] = Field(default_factory=list)
    candidate_id: UUID | None = None
    application_id: UUID | None = None
    document_id: UUID | None = None
    reference_no: str | None = None
    reused: bool = False
    budget_status: BudgetStatus | None = None
    # Frontend path, e.g. `/candidates/<id>?application=<id>`.
    link: str | None = None


class DraftCommitOut(BaseModel):
    mode: CommitMode
    results: list[DraftCommitRowOut]
    saved_count: int
    incomplete_count: int
    failed_count: int
    draft_deleted: bool


def issues_to_details(issues: list[RowIssue], index: int) -> list[dict[str, Any]]:
    return [{"row": index, "field": i.field, "message": i.message} for i in issues]
