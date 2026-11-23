"""Apply and read salary fields on Candidate rows."""

from __future__ import annotations

from decimal import Decimal

from app.models.candidate import Candidate
from app.models.enums import BudgetStatus, SalaryUnit
from app.schemas.salary import SalaryIn, SalaryOut, budget_status


def salary_out(
    amount: Decimal | None, currency: str, unit: SalaryUnit | str, negotiable: bool
) -> SalaryOut:
    unit_value = unit if isinstance(unit, SalaryUnit) else SalaryUnit(unit)
    return SalaryOut(
        amount=amount, currency=currency or "INR", unit=unit_value, negotiable=negotiable
    )


def current_salary(candidate: Candidate) -> SalaryOut:
    return salary_out(
        candidate.current_ctc,
        candidate.current_ctc_currency,
        candidate.current_ctc_unit,
        candidate.current_ctc_negotiable,
    )


def expected_salary(candidate: Candidate) -> SalaryOut:
    return salary_out(
        candidate.expected_ctc,
        candidate.expected_ctc_currency,
        candidate.expected_ctc_unit,
        candidate.expected_ctc_negotiable,
    )


def offered_salary(candidate: Candidate) -> SalaryOut:
    return salary_out(
        candidate.offered_ctc,
        candidate.offered_ctc_currency,
        candidate.offered_ctc_unit,
        candidate.offered_ctc_negotiable,
    )


def apply_salary(candidate: Candidate, prefix: str, body: SalaryIn | None) -> None:
    """Write a SalaryIn onto current_/expected_/offered_ columns. None clears the amount."""
    if body is None:
        return
    setattr(candidate, f"{prefix}_ctc", body.amount)
    setattr(candidate, f"{prefix}_ctc_currency", body.currency)
    setattr(candidate, f"{prefix}_ctc_unit", body.unit)
    setattr(candidate, f"{prefix}_ctc_negotiable", body.negotiable)


def candidate_budget(
    candidate: Candidate,
    job_salary_max: Decimal | None,
    job_salary_min: Decimal | None = None,
) -> BudgetStatus:
    return budget_status(
        candidate.expected_ctc,
        candidate.expected_ctc_unit,
        job_salary_max,
        job_salary_min,
    )
