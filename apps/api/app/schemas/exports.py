"""Request/response schemas for HR PDF and Excel exports."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class PdfSummaryOptions(BaseModel):
    include_salary: bool = False
    include_contact: bool = True
    include_hr_notes: bool = False


class PdfSummaryRequest(PdfSummaryOptions):
    """One or more applications; a single PDF for one id, otherwise a ZIP."""

    application_ids: list[UUID] = Field(min_length=1, max_length=200)


class ExcelExportRequest(BaseModel):
    """Optional explicit selection; when empty, current filters are used."""

    application_ids: list[UUID] = Field(default_factory=list, max_length=5000)
