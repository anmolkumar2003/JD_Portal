"""Phase 2: manual add candidate, salary, parse-cv, duplicates, budget badge."""

from decimal import Decimal
from io import BytesIO

import pytest
from httpx import AsyncClient

from app.models.enums import BudgetStatus, SalaryUnit
from app.schemas.salary import annualize, budget_status
from tests.conftest import login

pytestmark = pytest.mark.usefixtures("db")

# Minimal valid PDF magic + enough bytes for validate_cv
MINI_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n" + b" " * 200


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_annualize_and_budget() -> None:
    assert annualize(Decimal("100000"), SalaryUnit.PM) == Decimal("1200000")
    assert annualize(Decimal("1200000"), SalaryUnit.PA) == Decimal("1200000")
    assert budget_status(Decimal("2000000"), "pa", Decimal("1800000")) == BudgetStatus.ABOVE
    assert budget_status(Decimal("100000"), "pm", Decimal("1800000")) == BudgetStatus.WITHIN
    assert budget_status(None, "pa", Decimal("1800000")) == BudgetStatus.UNKNOWN


async def test_parse_cv_and_create_with_salary(client: AsyncClient) -> None:
    token = await login(client, "recruiter")
    headers = _auth(token)

    jobs = await client.get("/api/v1/jobs", headers=headers)
    assert jobs.status_code == 200
    job_id = jobs.json()["items"][0]["id"]

    created = await client.post(
        "/api/v1/candidates",
        headers=headers,
        data={
            "first_name": "Riya",
            "last_name": "Sharma",
            "email": "riya.sharma@example.com",
            "phone": "+91 98765 43210",
            "job_id": job_id,
            "expected_ctc_amount": "2500000",
            "expected_ctc_currency": "INR",
            "expected_ctc_unit": "pa",
            "expected_ctc_negotiable": "true",
            "current_ctc_amount": "1800000",
            "current_ctc_unit": "pa",
        },
        files={"cv": ("riya.pdf", BytesIO(MINI_PDF), "application/pdf")},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["candidate_id"]
    assert body["application_id"]
    assert body["reused"] is False
    assert body["budget_status"] in {"above", "within", "unknown"}

    detail = await client.get(f"/api/v1/applications/{body['application_id']}", headers=headers)
    assert detail.status_code == 200
    candidate = detail.json()["candidate"]
    assert candidate["expected_salary"]["amount"] == "2500000.00"
    assert candidate["expected_salary"]["negotiable"] is True
    assert candidate["current_salary"]["amount"] == "1800000.00"
    assert detail.json()["budget_status"] in {"above", "within", "unknown"}

    # Reuse by same email
    again = await client.post(
        "/api/v1/candidates",
        headers=headers,
        data={
            "first_name": "Riya",
            "last_name": "Sharma",
            "email": "riya.sharma@example.com",
            "phone": "+91 98765 43210",
        },
    )
    assert again.status_code == 201
    assert again.json()["reused"] is True
    assert again.json()["candidate_id"] == body["candidate_id"]


async def test_duplicates_and_profile_edit(client: AsyncClient) -> None:
    token = await login(client, "hradmin")
    headers = _auth(token)

    created = await client.post(
        "/api/v1/candidates",
        headers=headers,
        data={
            "first_name": "Aman",
            "last_name": "Gupta",
            "email": "aman.gupta@example.com",
            "phone": "+919811122233",
        },
    )
    assert created.status_code == 201
    candidate_id = created.json()["candidate_id"]

    dups = await client.get(
        "/api/v1/candidates/duplicates",
        headers=headers,
        params={"email": "aman.gupta@example.com", "phone": "9811122233"},
    )
    assert dups.status_code == 200
    matches = dups.json()["matches"]
    assert any(m["id"] == candidate_id for m in matches)
    assert any("email" in m["matched_on"] for m in matches)

    patched = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=headers,
        json={
            "current_title": "Senior Android Engineer",
            "expected_ctc": {
                "amount": "2200000",
                "currency": "INR",
                "unit": "pa",
                "negotiable": False,
            },
        },
    )
    assert patched.status_code == 200
    assert patched.json()["current_title"] == "Senior Android Engineer"
    assert patched.json()["expected_salary"]["amount"] == "2200000.00"
