"""Chatbot input cleaning: noise is removed, meaning and field mapping are preserved."""

from __future__ import annotations

import pytest

from app.cv_engine.quick_fill import parse_quick_fill
from app.cv_engine.quick_fill.text import clean_text


def _values(text: str) -> dict[str, str | None]:
    return {f.field: f.value for f in parse_quick_fill(text).fields}


def test_whitespace_tabs_and_blank_lines_are_collapsed() -> None:
    raw = "  Name:\t\tRahul   Sharma  \n\n\n\n   Email :  rahul@example.com   \n"
    assert clean_text(raw) == "Name: Rahul Sharma\n\nEmail: rahul@example.com"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("- Name: Rahul Sharma", "Name: Rahul Sharma"),
        ("* Name: Rahul Sharma", "Name: Rahul Sharma"),
        ("\u2022 Name: Rahul Sharma", "Name: Rahul Sharma"),
        ("1. Name: Rahul Sharma", "Name: Rahul Sharma"),
        ("2) Name: Rahul Sharma", "Name: Rahul Sharma"),
        ("**Name:** Rahul Sharma", "Name: Rahul Sharma"),
        ("`Name`: Rahul Sharma", "Name: Rahul Sharma"),
    ],
)
def test_list_markers_and_markdown_are_removed(raw: str, expected: str) -> None:
    assert clean_text(raw) == expected


def test_meaningful_text_is_preserved() -> None:
    assert clean_text("A. Kumar") == "A. Kumar"
    assert clean_text("john_doe@example.com") == "john_doe@example.com"
    assert clean_text("CTC 8,00,000") == "CTC 8,00,000"
    assert clean_text("Exp 3-5 yrs") == "Exp 3-5 yrs"


def test_repeated_separators_are_collapsed() -> None:
    assert clean_text("Pune ,, Maharashtra ;; India ,") == "Pune, Maharashtra; India"


def test_bulleted_structured_and_messy_text_give_the_same_fields() -> None:
    clean = "Name: Rahul Sharma\nEmail: rahul@example.com\nPhone: 9876543210\nLocation: Pune"
    messy = (
        "\n\n  \u2022  Name :\tRahul    Sharma\n\n\n"
        "  - Email:  rahul@example.com ,\n"
        "  * **Phone:** 9876543210\n\n\n  1. Location:  Pune  \n"
    )
    a, b = _values(clean), _values(messy)
    assert a == b
    assert b["email"] == "rahul@example.com"
    assert b["current_location"] == "Pune"


def test_unstructured_text_never_guesses_missing_values() -> None:
    values = _values("rahul sharma here, mail me on rahul@example.com")
    assert values.get("email") == "rahul@example.com"
    assert values.get("phone") is None
    assert values.get("current_ctc") is None
    assert values.get("current_location") is None
