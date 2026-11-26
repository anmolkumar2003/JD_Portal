"""Quick fill extractors, one table of varied examples per field.

Each row is "text -> what the field should be". `None` means the field must stay empty (the
engine must not guess). Texts are deliberately written in different styles: sentences, comma
lists, semicolons, "key: value" lines, abbreviations, lower case and Indian number formats.
"""

from typing import Any

import pytest

from app.cv_engine.quick_fill import QuickFillResult, parse_quick_fill


def value_of(text: str, field: str) -> Any:
    return parse_quick_fill(text).value(field)


def money(text: str, field: str) -> tuple[Any, ...] | None:
    value = value_of(text, field)
    if value is None:
        return None
    assert isinstance(value, dict)
    return (value["amount"], value["currency"], value["unit"])


def parse(text: str) -> QuickFillResult:
    return parse_quick_fill(text)


# --- Email ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "email"),
    [
        ("Rahul Sharma, Pune, rahul@mail.com", "rahul@mail.com"),
        ("email: Rahul.Sharma@Gmail.com", "rahul.sharma@gmail.com"),
        ("Email ID - priya_n@outlook.in", "priya_n@outlook.in"),
        ("contact amit+jobs@company.co.in for details", "amit+jobs@company.co.in"),
        ("mail id: neha.gupta@sub.domain.org", "neha.gupta@sub.domain.org"),
        ("e-mail: x@y.io, 5 years", "x@y.io"),
        ("5 years; rahul@mail.com; Pune", "rahul@mail.com"),
        ("rahul@mail.com", "rahul@mail.com"),
        ("My email is sneha.rao@example.com.", "sneha.rao@example.com"),
        ("EMAIL: ANIL@MAIL.COM", "anil@mail.com"),
        ("(vikram.s@mail.com)", "vikram.s@mail.com"),
        ("<karan@mail.com>", "karan@mail.com"),
        ("name: A B | email: a-b@mail-server.com", "a-b@mail-server.com"),
        ("reach me at ravi_kumar99@yahoo.co.uk please", "ravi_kumar99@yahoo.co.uk"),
        ("same@mail.com, same@mail.com", "same@mail.com"),
        ("Rahul, rahul@mail.com / 9876543210", "rahul@mail.com"),
    ],
)
def test_email(text: str, email: str) -> None:
    assert value_of(text, "email") == email


@pytest.mark.parametrize(
    "text",
    ["Rahul, Pune", "rahul@", "@mail.com", "rahul at mail dot com", "user@localhost", "5 years"],
)
def test_no_email(text: str) -> None:
    assert value_of(text, "email") is None


def test_two_different_emails_are_not_guessed() -> None:
    result = parse("Priya, personal p@x.com, work p@work.com")

    field = result.get("email")
    assert field is not None
    assert field.value is None
    assert {c.value for c in field.candidates} == {"p@x.com", "p@work.com"}
    assert field.warning


def test_labelled_email_wins_over_a_stray_one() -> None:
    result = parse("email: main@x.com, cc other@y.com")

    assert result.value("email") == "main@x.com"
    assert result.get("email") is not None
    assert result.get("email").warning  # type: ignore[union-attr]


# --- Phone ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "phone"),
    [
        ("Rahul, 9876543210", "+91 98765 43210"),
        ("phone: 98765 43210", "+91 98765 43210"),
        ("Mobile No: +91-98765-43210", "+91 98765 43210"),
        ("call +91 9876543210 after 5pm", "+91 98765 43210"),
        ("contact 09876543210", "+91 98765 43210"),
        ("whatsapp: 91 98765 43210", "+91 98765 43210"),
        ("Rahul; Pune; 98765-43210; 5 yrs", "+91 98765 43210"),
        ("ph: (+91) 98765 43210", "+91 98765 43210"),
        ("+1 415 555 2671", "+1 415 555 2671"),
        ("US number +1 (415) 555-2671", "+1 415 555 2671"),
        ("+44 7911 123456", "+44 7911123456"),
        ("tel: +971 50 123 4567", "+971 501234567"),
        ("pin 411001 mobile 9876543210", "+91 98765 43210"),
        ("9876543210 5 years", "+91 98765 43210"),
        ("Rahul 98765 43210 rahul@mail.com", "+91 98765 43210"),
        ("alt: 9123456789, phone: 9876543210", "+91 98765 43210"),
        ("number: 8123456789", "+91 81234 56789"),
    ],
)
def test_phone(text: str, phone: str) -> None:
    assert value_of(text, "phone") == phone


@pytest.mark.parametrize(
    "text",
    [
        "Rahul, Pune",
        "5 years, 30 days notice",
        "current 800000",
        "pin 411001",
        "12345",
        "alt phone: 9123456789",
        "DOB: 12-05-1995",
    ],
)
def test_no_phone(text: str) -> None:
    assert value_of(text, "phone") is None


def test_ten_digits_not_starting_6_to_9_is_kept_but_not_called_indian() -> None:
    field = parse("phone: 2345678901").get("phone")

    assert field is not None
    assert field.value == "2345678901"
    assert field.confidence != "high"


def test_two_unlabelled_numbers_are_not_guessed() -> None:
    field = parse("9876543210 and 9123456780").get("phone")

    assert field is not None
    assert field.value is None
    assert len(field.candidates) == 2


# --- Links ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "url"),
    [
        ("linkedin.com/in/rahul-s", "https://www.linkedin.com/in/rahul-s"),
        ("https://www.linkedin.com/in/rahul-s/", "https://www.linkedin.com/in/rahul-s"),
        ("http://linkedin.com/in/rahul", "https://www.linkedin.com/in/rahul"),
        ("www.linkedin.com/in/priya-nair-123", "https://www.linkedin.com/in/priya-nair-123"),
        (
            "LinkedIn: https://in.linkedin.com/in/amit-v?trk=abc",
            "https://www.linkedin.com/in/amit-v",
        ),
        ("linkedin: rahul-sharma", "https://www.linkedin.com/in/rahul-sharma"),
        ("Rahul, Pune, linkedin.com/in/rahul, 5 yrs", "https://www.linkedin.com/in/rahul"),
        ("profile https://uk.linkedin.com/in/neha", "https://www.linkedin.com/in/neha"),
    ],
)
def test_linkedin_url(text: str, url: str) -> None:
    assert value_of(text, "linkedin_url") == url


@pytest.mark.parametrize(
    ("text", "url"),
    [
        ("github.com/rahul", "https://github.com/rahul"),
        ("https://rahul.dev", "https://rahul.dev"),
        ("portfolio: rahulsharma.com", "https://rahulsharma.com"),
        ("website: https://www.priya.io/work", "https://www.priya.io/work"),
        ("behance.net/amit", "https://behance.net/amit"),
        ("www.myportfolio.in", "https://www.myportfolio.in"),
        ("portfolio https://kaggle.com/neha", "https://kaggle.com/neha"),
    ],
)
def test_portfolio_url(text: str, url: str) -> None:
    assert value_of(text, "portfolio_url") == url


@pytest.mark.parametrize(
    "text",
    ["mail@mail.com", "Rahul.Sharma", "e.g. and i.e. things", "5.5 years", "version 1.2.3", "a.b"],
)
def test_text_that_only_looks_like_a_link_is_left_alone(text: str) -> None:
    result = parse(text)

    assert result.value("portfolio_url") is None
    assert result.value("linkedin_url") is None


def test_linkedin_company_page_is_not_a_profile() -> None:
    assert value_of("https://www.linkedin.com/company/infosys", "linkedin_url") is None


# --- Experience -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "years"),
    [
        ("Rahul, 5 years", 5.0),
        ("5 yrs exp", 5.0),
        ("exp: 6.5 yrs", 6.5),
        ("experience 3 years 6 months", 3.5),
        ("total experience: 12 years", 12.0),
        ("7+ years of experience", 7.0),
        ("5y", 5.0),
        ("overall exp - 8.2 years", 8.2),
        ("fresher", 0.0),
        ("5 yoe", 5.0),
        ("Experience: 4", 4.0),
        ("exp 10", 10.0),
        ("five years", 5.0),
        ("five and a half years", 5.5),
        ("two years six months experience", 2.5),
        ("5 years, 8 LPA", 5.0),
        ("8 months of experience", 0.7),
        ("5 years in java, total experience 8 years", 8.0),
        ("total exp: 9 yrs; relevant exp: 4 yrs", 9.0),
        ("5 years 3 months", 5.3),
    ],
)
def test_experience(text: str, years: float) -> None:
    assert value_of(text, "total_experience_years") == pytest.approx(years)


@pytest.mark.parametrize(
    "text",
    [
        "Rahul, Pune",
        "30 days notice",
        "age: 30 years",
        "current 8 LPA",
        "5 years in java, 3 years in react",
        "experience: lots",
        "relevant exp: 4 yrs",
        "55 years of experience",
    ],
)
def test_experience_not_filled(text: str) -> None:
    assert value_of(text, "total_experience_years") is None


def test_experience_range_fills_the_maximum_and_offers_the_midpoint() -> None:
    field = parse("3-5 years").get("total_experience_years")

    assert field is not None
    assert field.value == pytest.approx(5.0)
    assert field.confidence != "high"
    assert [c.display for c in field.candidates] == ["3 years", "4 years", "5 years"]
    assert field.warning


def test_per_skill_experience_is_not_taken_as_the_total() -> None:
    field = parse("5 years in java, 3 years in react").get("total_experience_years")

    assert field is not None
    assert field.value is None
    assert len(field.candidates) == 2


# --- Notice period ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "days"),
    [
        ("30 days notice", 30),
        ("notice period: 60 days", 60),
        ("NP 2 months", 60),
        ("notice: 1 month", 30),
        ("notice 3 months", 90),
        ("immediate joiner", 0),
        ("can join immediately", 0),
        ("notice period - immediate", 0),
        ("serving notice, 20 days left", 20),
        ("np: 45", 45),
        ("notice period 15 days", 15),
        ("joining in 2 weeks", 14),
        ("available in 1 month", 30),
        ("90 days notice period", 90),
        ("Rahul, Pune, 30 days", 30),
        ("notice: 30d", 30),
        ("LWD in 15 days", 15),
        ("no notice", 0),
        ("np 1.5 months", 45),
    ],
)
def test_notice_period(text: str, days: int) -> None:
    assert value_of(text, "notice_period_days") == days


@pytest.mark.parametrize(
    "text",
    ["Rahul, Pune", "5 years", "current 8 LPA", "3 days a week in office", "negotiable notice"],
)
def test_notice_not_filled(text: str) -> None:
    assert value_of(text, "notice_period_days") is None


def test_notice_range_fills_the_maximum_and_offers_the_midpoint() -> None:
    field = parse("notice 30-60 days").get("notice_period_days")

    assert field is not None
    assert field.value == 60
    assert [c.value for c in field.candidates] == [30, 45, 60]


def test_serving_notice_without_days_asks_instead_of_guessing() -> None:
    field = parse("Rahul, serving notice").get("notice_period_days")

    assert field is not None
    assert field.value is None
    assert field.warning


# --- Salary: current, expected, offered -------------------------------------------------------

_INR_PA = "INR", "pa"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("current 8 LPA", (800000, "INR", "pa")),
        ("current CTC: 8,50,000", (850000, "INR", "pa")),
        ("CCTC 12 LPA", (1200000, "INR", "pa")),
        ("present salary 80k per month", (80000, "INR", "pm")),
        ("drawing 24 lakhs", (2400000, "INR", "pa")),
        ("currently earning ₹18,00,000 pa", (1800000, "INR", "pa")),
        ("Current CTC - 15L", (1500000, "INR", "pa")),
        ("last drawn 7 LPA", (700000, "INR", "pa")),
        ("existing package: 10 lakhs", (1000000, "INR", "pa")),
        ("current: $90k", (90000, "USD", "pa")),
        ("cctc 1.2 cr", (12000000, "INR", "pa")),
        ("current CTC is around 14 LPA", (1400000, "INR", "pa")),
        ("current 8", (800000, "INR", "pa")),
        ("CTC: 9.5 LPA", (950000, "INR", "pa")),
        ("salary 45000", (45000, "INR", "pm")),
        ("current salary Rs. 65,000/-", (65000, "INR", "pm")),
        ("Current CTC 8,00,000 per annum", (800000, "INR", "pa")),
        ("current 8.5 lacs", (850000, "INR", "pa")),
        ("c-ctc: 11 LPA", (1100000, "INR", "pa")),
    ],
)
def test_current_ctc(text: str, expected: tuple[Any, ...]) -> None:
    assert money(text, "current_ctc") == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("expected 12 LPA", (1200000, "INR", "pa")),
        ("ECTC: 15 LPA", (1500000, "INR", "pa")),
        ("expecting 20 lakhs", (2000000, "INR", "pa")),
        ("exp ctc 18L", (1800000, "INR", "pa")),
        ("expected CTC: 18,00,000", (1800000, "INR", "pa")),
        ("looking for 25 LPA", (2500000, "INR", "pa")),
        ("asking 30 LPA", (3000000, "INR", "pa")),
        ("expected salary 95k per month", (95000, "INR", "pm")),
        ("expectation: 16 LPA", (1600000, "INR", "pa")),
        ("expected: 12", (1200000, "INR", "pa")),
        ("e-ctc 14 lpa", (1400000, "INR", "pa")),
        ("expected package 40 lakhs", (4000000, "INR", "pa")),
        ("expecting $130k", (130000, "USD", "pa")),
        ("current 8 LPA, expected 12 LPA", (1200000, "INR", "pa")),
        ("ECTC 1.5 cr", (15000000, "INR", "pa")),
        ("expected ctc is 22 lacs", (2200000, "INR", "pa")),
    ],
)
def test_expected_ctc(text: str, expected: tuple[Any, ...]) -> None:
    assert money(text, "expected_ctc") == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("offered 10 LPA", (1000000, "INR", "pa")),
        ("offer: 11 lakhs", (1100000, "INR", "pa")),
        ("offered CTC 12,50,000", (1250000, "INR", "pa")),
        ("we offered 9.5 LPA", (950000, "INR", "pa")),
        ("offered package: 14 LPA", (1400000, "INR", "pa")),
        ("offered salary 70k per month", (70000, "INR", "pm")),
        ("Offered 18L", (1800000, "INR", "pa")),
        ("offer CTC 20 LPA", (2000000, "INR", "pa")),
        ("offered: 8 LPA, expected 10 LPA", (800000, "INR", "pa")),
        ("offered amount 15 lakhs", (1500000, "INR", "pa")),
        ("offered $100k", (100000, "USD", "pa")),
        ("offer of 13 LPA", (1300000, "INR", "pa")),
        ("offered 1 cr", (10000000, "INR", "pa")),
        ("offered ctc: 16 LPA", (1600000, "INR", "pa")),
        ("Offer 12 LPA; joining in 30 days", (1200000, "INR", "pa")),
    ],
)
def test_offered_ctc(text: str, expected: tuple[Any, ...]) -> None:
    assert money(text, "offered_ctc") == expected


@pytest.mark.parametrize(
    ("text", "current", "expected"),
    [
        ("CTC/ECTC: 8/12 LPA", (800000, "INR", "pa"), (1200000, "INR", "pa")),
        ("CCTC / ECTC 10 / 14 LPA", (1000000, "INR", "pa"), (1400000, "INR", "pa")),
        ("current/expected: 8 & 12 LPA", (800000, "INR", "pa"), (1200000, "INR", "pa")),
        ("ctc: 9, ectc: 13", (900000, "INR", "pa"), (1300000, "INR", "pa")),
        (
            "Current CTC: 8,00,000\nExpected CTC: 12,00,000",
            (800000, "INR", "pa"),
            (1200000, "INR", "pa"),
        ),
        ("expected 12 LPA, current 8 LPA", (800000, "INR", "pa"), (1200000, "INR", "pa")),
        ("8 LPA current and 12 LPA expected", (800000, "INR", "pa"), (1200000, "INR", "pa")),
        ("cctc 80k pm; ectc 1 lakh pm", (80000, "INR", "pm"), (100000, "INR", "pm")),
    ],
)
def test_current_and_expected_together(
    text: str, current: tuple[Any, ...], expected: tuple[Any, ...]
) -> None:
    assert money(text, "current_ctc") == current
    assert money(text, "expected_ctc") == expected


@pytest.mark.parametrize(
    "text",
    ["8 LPA", "35 lakhs", "$120k", "₹12,00,000", "80k per month", "8 LPA, 12 LPA", "Rahul, 10 LPA"],
)
def test_an_unlabelled_salary_is_never_assigned(text: str) -> None:
    result = parse(text)

    for name in ("current_ctc", "expected_ctc"):
        field = result.get(name)
        assert field is not None
        assert field.value is None
        assert field.candidates
        assert field.warning


def test_one_unlabelled_salary_offers_the_amount_as_a_choice() -> None:
    field = parse("Rahul, 10 LPA").get("current_ctc")

    assert field is not None
    assert [c.display for c in field.candidates] == ["10 LPA (₹10,00,000 per annum)"]


def _amount(value: object) -> object:
    return value.get("amount") if isinstance(value, dict) else None


def test_salary_range_fills_the_maximum_and_offers_low_mid_high() -> None:
    field = parse("expected 12-15 LPA").get("expected_ctc")

    assert field is not None
    assert field.value == {"amount": 1500000, "currency": "INR", "unit": "pa"}
    assert [_amount(c.value) for c in field.candidates] == [1200000, 1350000, 1500000]
    assert field.confidence != "high"
    assert field.warning


@pytest.mark.parametrize("text", ["in hand 70k", "expected 12 LPA but current in-hand 55k pm"])
def test_in_hand_pay_is_flagged_and_never_high_confidence(text: str) -> None:
    result = parse(text)
    fields = [f for f in result.fields if f.field.endswith("_ctc") and f.value is not None]

    assert fields
    for field in fields:
        if "in hand" in text and field.field == "current_ctc":
            assert field.confidence == "low"


def test_a_competing_offer_is_flagged() -> None:
    field = parse("another offer of 14 LPA from Zoho").get("offered_ctc")

    assert field is not None
    assert field.confidence == "low"
    assert field.value is None  # never filled: it is not our offer
    assert field.candidates
    assert field.warning


def test_two_different_amounts_for_the_same_label_are_not_guessed() -> None:
    field = parse("current 8 LPA, current 9 LPA").get("current_ctc")

    assert field is not None
    assert field.value is None
    assert len(field.candidates) == 2


@pytest.mark.parametrize("text", ["current 8 LPA", "expected 12 LPA", "no salary here"])
def test_nothing_is_offered_unless_the_text_says_so(text: str) -> None:
    assert parse(text).get("offered_ctc") is None


# --- Negotiable -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "field", "value"),
    [
        ("expected 12 LPA negotiable", "expected_ctc_negotiable", True),
        ("current 8 LPA, expected 12 LPA (negotiable)", "expected_ctc_negotiable", True),
        ("expected 12 LPA non-negotiable", "expected_ctc_negotiable", False),
        ("expected 12 LPA, not negotiable", "expected_ctc_negotiable", False),
        ("ECTC: 15 LPA nego", "expected_ctc_negotiable", True),
        ("current 8 LPA negotiable", "current_ctc_negotiable", True),
        ("expected 12 LPA, negotiable", "expected_ctc_negotiable", True),
        ("expected ctc: 14 LPA (neg)", "expected_ctc_negotiable", True),
        ("only expected 20 lakhs, negotiable", "expected_ctc_negotiable", True),
        ("offered 10 LPA negotiable", "offered_ctc_negotiable", True),
        ("expected CTC: 12 LPA - open to negotiation", "expected_ctc_negotiable", True),
        ("ectc 18L negotiable, np 30 days", "expected_ctc_negotiable", True),
        ("expected 12 LPA; negotiable: yes", "expected_ctc_negotiable", True),
        ("expected 12 LPA; negotiable: no", "expected_ctc_negotiable", False),
        ("expected: 25 LPA, flexible negotiable", "expected_ctc_negotiable", True),
    ],
)
def test_negotiable(text: str, field: str, value: bool) -> None:
    assert value_of(text, field) is value


def test_negotiable_notice_period_is_not_a_negotiable_salary() -> None:
    result = parse("30 days notice negotiable")

    assert result.value("expected_ctc_negotiable") is None
    assert result.value("current_ctc_negotiable") is None


def test_negotiable_far_from_any_salary_asks_which_one() -> None:
    result = parse("current 8 LPA, expected 12 LPA, Pune, 5 years, negotiable")

    for name in ("current_ctc_negotiable", "expected_ctc_negotiable"):
        field = result.get(name)
        assert field is not None
        assert field.value is None
        assert field.candidates
