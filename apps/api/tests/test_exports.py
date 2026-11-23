"""Candidate PDF summary and Excel export (HR admin only)."""

from __future__ import annotations

import io
import zipfile
from io import BytesIO
from uuid import uuid4

import pytest
from httpx import AsyncClient
from openpyxl import load_workbook
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.compliance import AuditLog
from app.services import exports as exports_mod
from app.services.excel_export import EXCEL_MAX_ROWS, build_candidates_workbook
from app.services.exports_common import sanitize_spreadsheet_value
from app.services.pdf_summary import build_pdf_summary
from tests.conftest import login

pytestmark = pytest.mark.usefixtures("db")

MINI_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n" + b" " * 200


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_application(
    client: AsyncClient, headers: dict[str, str], **extra: str
) -> dict[str, str]:
    jobs = await client.get("/api/v1/jobs", headers=headers)
    assert jobs.status_code == 200
    job_id = str(jobs.json()["items"][0]["id"])
    email = extra.pop("email", f"export-{uuid4().hex[:8]}@example.com")
    created = await client.post(
        "/api/v1/candidates",
        headers=headers,
        data={
            "first_name": extra.pop("first_name", "Export"),
            "last_name": extra.pop("last_name", "Candidate"),
            "email": email,
            "phone": extra.pop("phone", "+91 90000 00001"),
            "job_id": job_id,
            "current_title": "Engineer",
            "current_company": "Acme Labs",
            **extra,
        },
        files={"cv": ("cv.pdf", BytesIO(MINI_PDF), "application/pdf")},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    return {
        "candidate_id": str(body["candidate_id"]),
        "application_id": str(body["application_id"]),
    }


def test_sanitize_spreadsheet_formula_injection() -> None:
    assert sanitize_spreadsheet_value("=1+1") == "'=1+1"
    assert sanitize_spreadsheet_value("+cmd") == "'+cmd"
    assert sanitize_spreadsheet_value("-1") == "'-1"
    assert sanitize_spreadsheet_value("@SUM(A1)") == "'@SUM(A1)"
    assert sanitize_spreadsheet_value("normal") == "normal"
    assert sanitize_spreadsheet_value(42) == 42


def test_pdf_summary_contains_advisory_and_name() -> None:
    pdf = build_pdf_summary(
        {
            "org_name": "Demo Org",
            "candidate_name": "Priya Sharma",
            "current_title": "Android Developer",
            "current_company": "Pixel Co",
            "job_title": "Senior Android Developer",
            "department": "Engineering",
            "stage": "Screening",
            "is_shortlisted": True,
            "include_contact": True,
            "include_salary": False,
            "include_hr_notes": False,
            "email": "priya@example.com",
            "phone": "+91 11111 22222",
            "location": "Bengaluru",
            "experience_lines": ["Android Developer — Pixel Co — 2020-2024"],
            "education_lines": ["B.Tech — NIT"],
            "top_skills": ["Kotlin", "Compose"],
            "match_score": 82,
            "matched_skills": ["Kotlin"],
            "missing_skills": ["Compose"],
            "ats_score": 75,
            "interview_ratings": [
                {
                    "round_name": "Tech",
                    "overall_rating": 4,
                    "recommendation": "yes",
                    "skill_ratings": [{"skill": "Kotlin", "rating": 4}],
                    "strengths": "Solid Kotlin",
                    "concerns": "Compose depth",
                }
            ],
            "generated_at": "2026-11-23 10:00 UTC",
        }
    )
    reader = PdfReader(io.BytesIO(pdf))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Priya Sharma" in text
    assert "Demo Org" in text
    assert "advisory" in text.lower()
    assert "priya@example.com" in text
    assert "Kotlin" in text


def test_excel_workbook_injection_and_meta() -> None:
    content = build_candidates_workbook(
        [
            {
                "Name": '=HYPERLINK("http://evil")',
                "Email": "a@example.com",
                "Phone": "+123",
                "Location": "Delhi",
                "Job": "Engineer",
                "Department": "Eng",
                "Stage": "Applied",
                "Source": "manual",
                "Current company": "Co",
                "Current title": "Dev",
                "Total experience": 3,
                "Notice period (days)": 30,
                "Current CTC": "INR 10.00 pa",
                "Expected CTC": "INR 12.00 pa",
                "Offered CTC": "",
                "Above budget": "No",
                "Match score": 70,
                "ATS score": 60,
                "Average interview rating": 4.0,
                "Recommendation": "yes",
                "Shortlisted": "No",
                "Tags": "fast",
                "Applied date": "2026-11-01",
            }
        ],
        filters_used={"stage_id": "abc", "q": "(set, 3 chars)"},
        selection_mode="filters",
    )
    wb = load_workbook(io.BytesIO(content))
    ws = wb["Candidates"]
    assert ws["A1"].value == "Name"
    assert ws.freeze_panes == "A2"
    assert ws.auto_filter.ref
    assert str(ws["A2"].value).startswith("'=")
    meta = wb["Export info"]
    assert meta["B2"].value == 1
    assert meta["B3"].value == "filters"


async def test_pdf_export_hr_only_and_audit(
    client: AsyncClient, db: async_sessionmaker[AsyncSession]
) -> None:
    recruiter = await login(client, "recruiter")
    created = await _create_application(client, _auth(recruiter))
    app_id = created["application_id"]

    denied = await client.post(
        "/api/v1/exports/pdf-summaries",
        headers=_auth(recruiter),
        json={"application_ids": [app_id]},
    )
    assert denied.status_code == 403

    hr = await login(client, "hradmin")
    ok = await client.post(
        "/api/v1/exports/pdf-summaries",
        headers=_auth(hr),
        json={
            "application_ids": [app_id],
            "include_contact": True,
            "include_salary": False,
            "include_hr_notes": False,
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.headers["content-type"].startswith("application/pdf")
    assert "attachment" in ok.headers.get("content-disposition", "")
    reader = PdfReader(io.BytesIO(ok.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Export Candidate" in text
    assert "advisory" in text.lower()

    async with db() as session:
        logs = list(
            await session.scalars(
                select(AuditLog).where(AuditLog.action == "candidates.pdf_exported")
            )
        )
    assert logs
    latest = logs[-1]
    assert latest.diff.get("count") == 1
    assert "email" not in latest.diff
    assert "Export" not in str(latest.diff)


async def test_pdf_bulk_zip(client: AsyncClient) -> None:
    hr = await login(client, "hradmin")
    headers = _auth(hr)
    a = await _create_application(
        client, headers, first_name="One", email=f"one-{uuid4().hex[:6]}@ex.com"
    )
    b = await _create_application(
        client, headers, first_name="Two", email=f"two-{uuid4().hex[:6]}@ex.com"
    )
    resp = await client.post(
        "/api/v1/exports/pdf-summaries",
        headers=headers,
        json={"application_ids": [a["application_id"], b["application_id"]]},
    )
    assert resp.status_code == 200
    assert "zip" in resp.headers["content-type"]
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        names = zf.namelist()
        assert len(names) == 2
        assert all(n.endswith(".pdf") for n in names)


async def test_excel_export_filters_roles_empty_and_injection(
    client: AsyncClient, db: async_sessionmaker[AsyncSession]
) -> None:
    hr = await login(client, "hradmin")
    headers = _auth(hr)
    await _create_application(
        client,
        headers,
        first_name="Excel",
        last_name="Row",
        email=f"excel-{uuid4().hex[:6]}@example.com",
        phone="+91 98888 77777",
    )

    recruiter = await login(client, "recruiter")
    denied = await client.get("/api/v1/exports/excel", headers=_auth(recruiter))
    assert denied.status_code == 403

    empty = await client.get(
        "/api/v1/exports/excel",
        headers=headers,
        params={"q": "zzznomatch-export-empty"},
    )
    assert empty.status_code == 200
    wb_empty = load_workbook(io.BytesIO(empty.content))
    assert wb_empty["Candidates"]["A1"].value == "Name"
    assert wb_empty["Export info"]["B2"].value == 0

    ok = await client.get(
        "/api/v1/exports/excel",
        headers=headers,
        params={"q": "Excel Row"},
    )
    assert ok.status_code == 200
    assert "spreadsheetml" in ok.headers["content-type"]
    wb = load_workbook(io.BytesIO(ok.content))
    ws = wb["Candidates"]
    names = [ws.cell(row=r, column=1).value for r in range(2, ws.max_row + 1)]
    assert any(n and "Excel" in str(n) for n in names)

    async with db() as session:
        logs = list(
            await session.scalars(
                select(AuditLog).where(AuditLog.action == "candidates.excel_exported")
            )
        )
    assert logs
    assert logs[-1].diff.get("row_count") is not None
    assert "98888" not in str(logs[-1].diff)


async def test_excel_selected_ids(client: AsyncClient) -> None:
    hr = await login(client, "hradmin")
    headers = _auth(hr)
    a = await _create_application(client, headers, email=f"sel-a-{uuid4().hex[:6]}@ex.com")
    await _create_application(client, headers, email=f"sel-b-{uuid4().hex[:6]}@ex.com")
    resp = await client.get(
        "/api/v1/exports/excel",
        headers=headers,
        params=[("application_ids", a["application_id"])],
    )
    assert resp.status_code == 200
    wb = load_workbook(io.BytesIO(resp.content))
    assert wb["Export info"]["B2"].value == 1
    assert wb["Export info"]["B3"].value == "selected"


async def test_excel_limit_message(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """When filters match more than the cap, return a clear 400."""
    monkeypatch.setattr(exports_mod, "EXCEL_MAX_ROWS", 0)
    hr = await login(client, "hradmin")
    resp = await client.get("/api/v1/exports/excel", headers=_auth(hr))
    if resp.status_code == 200:
        await _create_application(client, _auth(hr), email=f"lim-{uuid4().hex[:6]}@ex.com")
        resp = await client.get("/api/v1/exports/excel", headers=_auth(hr))
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "export_limit"
    assert "limited" in body["error"]["message"].lower()


def test_excel_max_constant() -> None:
    assert EXCEL_MAX_ROWS == 5000
