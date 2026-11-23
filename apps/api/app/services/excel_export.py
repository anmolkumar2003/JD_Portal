"""Build candidate Excel workbooks with openpyxl (MIT)."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.services.exports_common import sanitize_spreadsheet_value

EXCEL_MAX_ROWS = 5000

# Column headers in export order
EXCEL_COLUMNS: tuple[str, ...] = (
    "Name",
    "Email",
    "Phone",
    "Location",
    "Job",
    "Department",
    "Stage",
    "Source",
    "Current company",
    "Current title",
    "Total experience",
    "Notice period (days)",
    "Current CTC",
    "Expected CTC",
    "Offered CTC",
    "Above budget",
    "Match score",
    "ATS score",
    "Average interview rating",
    "Recommendation",
    "Shortlisted",
    "Tags",
    "Applied date",
)

_HEADER_FILL = PatternFill("solid", fgColor="4F46E5")
_HEADER_FONT = Font(bold=True, color="FFFFFF")


def _autosize(ws: Worksheet, widths: dict[int, float]) -> None:
    for idx, width in widths.items():
        ws.column_dimensions[get_column_letter(idx)].width = width


def build_candidates_workbook(
    rows: list[dict[str, Any]],
    *,
    filters_used: dict[str, str],
    selection_mode: str,
) -> bytes:
    """Return .xlsx bytes. `rows` are already sanitized dicts keyed by EXCEL_COLUMNS."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Candidates"

    for col, header in enumerate(EXCEL_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")

    for r_idx, row in enumerate(rows, start=2):
        for c_idx, header in enumerate(EXCEL_COLUMNS, start=1):
            value = sanitize_spreadsheet_value(row.get(header))
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            if header in {
                "Match score",
                "ATS score",
                "Average interview rating",
                "Total experience",
            }:
                if isinstance(value, (int, float)):
                    cell.number_format = "0.0" if header == "Average interview rating" else "0"
            if header == "Applied date" and isinstance(value, str) and "T" in value:
                cell.number_format = "YYYY-MM-DD"

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(EXCEL_COLUMNS))}{max(1, len(rows) + 1)}"
    _autosize(
        ws,
        {
            1: 22,
            2: 28,
            3: 16,
            4: 16,
            5: 28,
            6: 16,
            7: 14,
            8: 12,
            9: 18,
            10: 18,
            11: 12,
            12: 14,
            13: 20,
            14: 20,
            15: 20,
            16: 12,
            17: 12,
            18: 10,
            19: 14,
            20: 14,
            21: 12,
            22: 20,
            23: 14,
        },
    )

    meta = wb.create_sheet("Export info")
    meta["A1"] = "Generated at"
    meta["B1"] = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    meta["A2"] = "Row count"
    meta["B2"] = len(rows)
    meta["A3"] = "Selection"
    meta["B3"] = selection_mode
    meta["A4"] = "Max rows"
    meta["B4"] = EXCEL_MAX_ROWS
    meta["A6"] = "Filters used"
    meta["B6"] = "(none)" if not filters_used else ""
    r = 7
    for key, value in sorted(filters_used.items()):
        meta.cell(row=r, column=1, value=sanitize_spreadsheet_value(key))
        meta.cell(row=r, column=2, value=sanitize_spreadsheet_value(value))
        r += 1
    meta.column_dimensions["A"].width = 28
    meta.column_dimensions["B"].width = 48
    for cell in (meta["A1"], meta["A2"], meta["A3"], meta["A4"], meta["A6"]):
        cell.font = Font(bold=True)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
