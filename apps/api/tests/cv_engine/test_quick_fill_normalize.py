"""Quick fill normalizers: phone, experience (years), notice (days) and salary."""

from decimal import Decimal

import pytest

from app.cv_engine.quick_fill.normalize import (
    format_money,
    indian_group,
    normalize_experience,
    normalize_notice,
    normalize_phone,
    normalize_salary,
)

# --- Phone ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "display"),
    [
        ("9876543210", "+91 98765 43210"),
        ("98765 43210", "+91 98765 43210"),
        ("98765-43210", "+91 98765 43210"),
        ("+91 9876543210", "+91 98765 43210"),
        ("+91-98765-43210", "+91 98765 43210"),
        ("+919876543210", "+91 98765 43210"),
        ("919876543210", "+91 98765 43210"),
        ("09876543210", "+91 98765 43210"),
        ("+91 (98765) 43210", "+91 98765 43210"),
        ("(+91) 98765 43210", "+91 98765 43210"),
        ("+910 9876543210", "+91 98765 43210"),
        ("6123456789", "+91 61234 56789"),
        ("+1 415 555 2671", "+1 415 555 2671"),
        ("+44 7911 123456", "+44 7911123456"),
        ("+971 50 123 4567", "+971 501234567"),
        ("0044 7911 123456", "+44 7911123456"),
    ],
)
def test_phone_is_put_in_a_standard_format(raw: str, display: str) -> None:
    phone = normalize_phone(raw)

    assert phone is not None
    assert phone.display == display


@pytest.mark.parametrize("raw", ["12345", "abc", "", "98765", "1" * 20, "123-45"])
def test_phone_rejects_things_that_are_not_numbers(raw: str) -> None:
    assert normalize_phone(raw) is None


@pytest.mark.parametrize("raw", ["2345678901", "04412345678", "4412345678"])
def test_phone_without_country_code_is_not_guessed_as_indian(raw: str) -> None:
    phone = normalize_phone(raw)

    assert phone is not None
    assert phone.kind == "unclear"
    assert not phone.display.startswith("+91")


# --- Experience -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "years"),
    [
        ("5 years", "5.0"),
        ("5 yrs", "5.0"),
        ("5yrs", "5.0"),
        ("5 y", "5.0"),
        ("5.5 years", "5.5"),
        ("5+ years", "5.0"),
        ("5 years 3 months", "5.3"),
        ("5 yrs 6 months", "5.5"),
        ("5 years and 6 months", "5.5"),
        ("2 years 1 month", "2.1"),
        ("0 years 8 months", "0.7"),
        ("8 months", "0.7"),
        ("18 months", "1.5"),
        ("6 yoe", "6.0"),
        ("fresher", "0.0"),
        ("no experience", "0.0"),
        ("12 years", "12.0"),
        ("5.25 years", "5.3"),
    ],
)
def test_experience_is_a_decimal_number_of_years(text: str, years: str) -> None:
    result = normalize_experience(text)

    assert result is not None
    assert result.value == Decimal(years)


@pytest.mark.parametrize(
    ("text", "low", "high"), [("3-5 years", "3.0", "5.0"), ("3 to 5 yrs", "3.0", "5.0")]
)
def test_experience_range_keeps_both_ends(text: str, low: str, high: str) -> None:
    result = normalize_experience(text)

    assert result is not None
    assert result.low == Decimal(low)
    assert result.value == Decimal(high)


@pytest.mark.parametrize("text", ["", "lots", "experienced", "years"])
def test_experience_not_found(text: str) -> None:
    assert normalize_experience(text) is None


# --- Notice -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "days"),
    [
        ("30 days", 30),
        ("30 d", 30),
        ("30days", 30),
        ("15 days", 15),
        ("45 days", 45),
        ("90 days", 90),
        ("1 month", 30),
        ("2 months", 60),
        ("3 months", 90),
        ("1.5 months", 45),
        ("1 week", 7),
        ("2 weeks", 14),
        ("4 weeks", 28),
        ("immediate", 0),
        ("immediately", 0),
        ("immediate joiner", 0),
        ("can join immediately", 0),
        ("no notice", 0),
        ("serving 20 days", 20),
    ],
)
def test_notice_is_converted_to_days(text: str, days: int) -> None:
    result = normalize_notice(text)

    assert result is not None
    assert result.value == Decimal(days)


def test_notice_range_keeps_both_ends() -> None:
    result = normalize_notice("30-60 days")

    assert result is not None
    assert (result.low, result.value) == (Decimal(30), Decimal(60))


@pytest.mark.parametrize("text", ["", "soon", "negotiable"])
def test_notice_not_found(text: str) -> None:
    assert normalize_notice(text) is None


# --- Salary -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "amount", "currency", "unit"),
    [
        ("8 LPA", 800000, "INR", "pa"),
        ("8.5 LPA", 850000, "INR", "pa"),
        ("8 lakhs", 800000, "INR", "pa"),
        ("8 lacs", 800000, "INR", "pa"),
        ("8L", 800000, "INR", "pa"),
        ("8 lakh per annum", 800000, "INR", "pa"),
        ("12 lakhs pa", 1200000, "INR", "pa"),
        ("1.2 cr", 12000000, "INR", "pa"),
        ("1 crore", 10000000, "INR", "pa"),
        ("8,00,000", 800000, "INR", "pa"),
        ("800000", 800000, "INR", "pa"),
        ("₹8,00,000", 800000, "INR", "pa"),
        ("Rs. 8,00,000", 800000, "INR", "pa"),
        ("INR 12,00,000 per annum", 1200000, "INR", "pa"),
        ("80k per month", 80000, "INR", "pm"),
        ("80,000 pm", 80000, "INR", "pm"),
        ("80000 monthly", 80000, "INR", "pm"),
        ("45000", 45000, "INR", "pm"),
        ("$120k", 120000, "USD", "pa"),
        ("$120,000 per annum", 120000, "USD", "pa"),
        ("USD 8000 per month", 8000, "USD", "pm"),
        ("£50,000", 50000, "GBP", "pa"),
        ("€4000 pm", 4000, "EUR", "pm"),
    ],
)
def test_salary_becomes_amount_currency_and_unit(
    text: str, amount: int, currency: str, unit: str
) -> None:
    money = normalize_salary(text)

    assert money is not None
    assert money.value.amount == Decimal(amount)
    assert money.value.currency == currency
    assert money.value.unit == unit


@pytest.mark.parametrize(
    ("text", "low", "high"),
    [
        ("12-15 LPA", 1200000, 1500000),
        ("10 to 12 lakhs", 1000000, 1200000),
        ("15-12 LPA", 1200000, 1500000),
    ],
)
def test_salary_range_keeps_both_ends(text: str, low: int, high: int) -> None:
    money = normalize_salary(text)

    assert money is not None
    assert money.low is not None
    assert money.low.amount == Decimal(low)
    assert money.value.amount == Decimal(high)
    assert money.midpoint is not None
    assert money.midpoint.amount == Decimal(low + high) / 2


@pytest.mark.parametrize("text", ["", "negotiable", "good package"])
def test_salary_not_found(text: str) -> None:
    assert normalize_salary(text) is None


def test_a_guessed_unit_is_explained() -> None:
    money = normalize_salary("45000")

    assert money is not None
    assert money.value.assumed is not None
    assert "per month" in money.value.assumed


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (0, "0"),
        (999, "999"),
        (1000, "1,000"),
        (80000, "80,000"),
        (800000, "8,00,000"),
        (1200000, "12,00,000"),
        (12000000, "1,20,00,000"),
    ],
)
def test_indian_digit_grouping(value: int, text: str) -> None:
    assert indian_group(value) == text


def test_money_is_formatted_for_people() -> None:
    money = normalize_salary("8 LPA")

    assert money is not None
    assert format_money(money.value) == "8 LPA (₹8,00,000 per annum)"
