"""Input styles added after the first accuracy run: sentences, emoji separators, labels without a
colon, several candidates on separate lines, other currencies and competing offers."""

from __future__ import annotations

import pytest

from app.cv_engine.quick_fill import parse_quick_fill
from app.cv_engine.quick_fill.types import Json


def value_of(text: str, name: str) -> Json:
    return parse_quick_fill(text).value(name)


SENTENCES = (
    "Candidate: Varun Sethi. Currently in Pune. 6 years of experience. Current CTC is 17 LPA. "
    "Expected CTC is 22 LPA. Can join in 45 days."
)


def test_full_stops_separate_sentences() -> None:
    result = parse_quick_fill(SENTENCES)

    assert result.value("first_name") == "Varun"
    assert result.value("last_name") == "Sethi"
    assert result.value("current_location") == "Pune"
    assert result.value("total_experience_years") == 6
    assert result.value("notice_period_days") == 45
    assert result.value("current_ctc") == {"amount": 1700000, "currency": "INR", "unit": "pa"}
    assert result.value("expected_ctc") == {"amount": 2200000, "currency": "INR", "unit": "pa"}


@pytest.mark.parametrize(
    ("text", "field", "expected"),
    [
        ("C. Ramesh, Chennai", "first_name", "C"),  # an initial is not a sentence end
        ("Dr. Anita Rao, Pune", "first_name", "Anita"),
        ("Exp. 5 years, Pune", "total_experience_years", 5),
        ("Rahul Sharma, Pune, Infosys Pvt. Ltd., 5 years", "current_company", "Infosys"),
        (
            "current salary Rs. 65,000/-",
            "current_ctc",
            {"amount": 65000, "currency": "INR", "unit": "pm"},
        ),
        ("Rahul Sharma, 5.5 years, Pune", "total_experience_years", 5.5),
    ],
)
def test_abbreviations_and_decimals_do_not_split(text: str, field: str, expected: Json) -> None:
    assert value_of(text, field) == expected


def test_emoji_separate_facts() -> None:
    text = "\U0001f464 Maya Krishnan \U0001f4cd Chennai \U0001f4bc 6 years \U0001f4e7 maya@mail.com"
    result = parse_quick_fill(text)

    assert result.value("first_name") == "Maya"
    assert result.value("current_location") == "Chennai"
    assert result.value("total_experience_years") == 6
    assert result.value("email") == "maya@mail.com"


def test_labels_after_each_other_without_commas() -> None:
    result = parse_quick_fill("email: tarun@mail.com phone: 9988776655 name: Tarun Das")

    assert result.value("email") == "tarun@mail.com"
    assert result.value("first_name") == "Tarun"
    assert result.value("last_name") == "Das"
    assert result.value("phone") == "+91 99887 76655"


@pytest.mark.parametrize(
    ("text", "field", "expected"),
    [
        ("Pune, current location Chennai", "current_location", "Chennai"),
        ("Rahul, current company Infosys", "current_company", "Infosys"),
        ("Rahul, total experience 5 years", "total_experience_years", 5),
        ("Rahul, notice period 30 days", "notice_period_days", 30),
        ("Rahul, notice period is 45 days", "notice_period_days", 45),
        ("Rahul, NP 45", "notice_period_days", 45),
        (
            "Rahul, expected ctc 18 lpa",
            "expected_ctc",
            {"amount": 1800000, "currency": "INR", "unit": "pa"},
        ),
    ],
)
def test_two_word_labels_need_no_colon(text: str, field: str, expected: Json) -> None:
    assert value_of(text, field) == expected


def test_sentence_openers_are_not_taken_as_labels() -> None:
    # "working for" / "years of experience" must keep going through the sentence rules
    assert value_of("Rahul, 6 years of experience", "total_experience_years") == 6
    assert value_of("working for Capgemini since 2019", "current_company") == "Capgemini"


def test_a_title_after_the_company() -> None:
    result = parse_quick_fill("Mohit Arora, working at Cognizant as Senior Associate")

    assert result.value("current_company") == "Cognizant"
    assert result.value("current_title") == "Senior Associate"


def test_between_two_amounts_is_a_range() -> None:
    field = parse_quick_fill("expected between 10 and 12 LPA").get("expected_ctc")

    assert field is not None
    assert field.value == {"amount": 1200000, "currency": "INR", "unit": "pa"}
    assert field.confidence == "medium"
    assert field.warning


def test_gulf_currencies_are_kept() -> None:
    result = parse_quick_fill("Manoj, current AED 15000 per month, expected AED 18000 per month")

    assert result.value("current_ctc") == {"amount": 15000, "currency": "AED", "unit": "pm"}
    assert result.value("expected_ctc") == {"amount": 18000, "currency": "AED", "unit": "pm"}


def test_an_offer_from_another_company_is_never_filled() -> None:
    field = parse_quick_fill("Karan Johar, current 30 lpa, offered 36 lpa by Flipkart").get(
        "offered_ctc"
    )

    assert field is not None
    assert field.value is None
    assert [c.display for c in field.candidates]
    assert field.warning and "competing" in field.warning


def test_unfamiliar_two_word_name_is_offered_not_ticked() -> None:
    # spaCy reads "Ritu Agarwal" as an organisation and the first-name list lacks Ritu.
    field = parse_quick_fill("Ritu Agarwal\nJaipur\n3 years").get("first_name")

    assert field is not None
    assert field.value == "Ritu"
    assert field.confidence == "medium"  # medium rows start unticked in the preview


def test_a_skill_word_is_not_a_name() -> None:
    result = parse_quick_fill("knows docker")

    assert result.value("skills") == ["Docker"]
    assert result.get("first_name") is None


def test_state_and_country_complete_a_city() -> None:
    assert value_of("Pune, Maharashtra, India", "current_location") == "Pune, Maharashtra"


@pytest.mark.parametrize(
    "text",
    [
        "Rahul Sharma, Pune, 5 years\nPriya Nair, Mumbai, 3 years",
        "Rahul Sharma, Pune, 5 years, 8 LPA\nPriya Nair, Mumbai, 3 years, 6 LPA\nAmit Verma, Noida, 7 yrs, 18 LPA",
    ],
)
def test_lines_that_each_describe_a_person_are_several_candidates(text: str) -> None:
    result = parse_quick_fill(text)

    assert result.multiple_candidates
    assert result.fields == []  # never mixed
    assert len(result.segments) >= 2


@pytest.mark.parametrize(
    "text",
    [
        "Ritu Agarwal\nJaipur\n3 years\n7 LPA\n30 days",  # one person written one fact per line
        "Name: Priya Nair\nEmail: p@x.com\nLocation: Pune",
        "Rahul Sharma\nPune",
    ],
)
def test_one_fact_per_line_is_still_one_person(text: str) -> None:
    result = parse_quick_fill(text)

    assert not result.multiple_candidates
    assert result.fields
