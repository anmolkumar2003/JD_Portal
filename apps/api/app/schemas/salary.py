"""Salary amount + currency + unit + negotiable, used on candidates."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.models.enums import BudgetStatus, SalaryUnit

CurrencyCode = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Z]{3}$")
]
Money = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


class SalaryIn(BaseModel):
    amount: Money | None = None
    currency: CurrencyCode = "INR"
    unit: SalaryUnit = SalaryUnit.PA
    negotiable: bool = False


class SalaryOut(BaseModel):
    amount: Decimal | None
    currency: str
    unit: SalaryUnit
    negotiable: bool


def annualize(amount: Decimal | None, unit: SalaryUnit | str | None) -> Decimal | None:
    """Convert a salary to per-annum for comparison with job bands."""
    if amount is None:
        return None
    value = unit.value if isinstance(unit, SalaryUnit) else (unit or "pa")
    return amount * 12 if value == SalaryUnit.PM.value else amount


def budget_status(
    expected_amount: Decimal | None,
    expected_unit: SalaryUnit | str | None,
    salary_max: Decimal | None,
    salary_min: Decimal | None = None,
) -> BudgetStatus:
    """Advisory only. Above = expected annual CTC exceeds the job band maximum."""
    annual = annualize(expected_amount, expected_unit)
    if annual is None or salary_max is None:
        return BudgetStatus.UNKNOWN
    if annual > salary_max:
        return BudgetStatus.ABOVE
    if salary_min is not None and annual < salary_min:
        return (
            BudgetStatus.WITHIN
        )  # below band still "within" for amber/green UX; green = not above
    return BudgetStatus.WITHIN


BudgetLabel = Literal["above", "within", "unknown"]
