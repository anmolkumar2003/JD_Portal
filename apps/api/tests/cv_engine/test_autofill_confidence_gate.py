"""Autofill must omit uncertain fields so wrong values are never persisted (CV-03)."""

from __future__ import annotations

from types import SimpleNamespace

from app.cv_engine.parser import AUTOFILL_MIN_CONFIDENCE, RuleBasedParser
from app.services.cv_processing import _fill_candidate

MISMAPPED_CV = """
Professional Summary
Platform engineer focused on reliability.

John Smith
john.smith@example.com | +91 98765 43210

Experience
Senior Engineer
Acme Corp
Jan 2020 – Present
Built Python services.

Projects
Mumbai Port Digitization Platform
Work spanning Singapore and Dubai.

Skills
Python, FastAPI, PostgreSQL
"""


def _empty_candidate() -> SimpleNamespace:
    return SimpleNamespace(
        first_name="",
        last_name="",
        email="",
        phone="",
        current_location="",
        total_experience_years=None,
        linkedin_url=None,
        portfolio_url=None,
        current_title="",
        current_company="",
    )


def test_fill_candidate_keeps_correct_identity_across_save() -> None:
    parsed = RuleBasedParser().parse(MISMAPPED_CV)
    assert parsed.full_name == "John Smith"
    assert parsed.confidence.get("name", 0) >= AUTOFILL_MIN_CONFIDENCE

    candidate = _empty_candidate()
    _fill_candidate(
        candidate,
        parsed.to_data_dict(),
        parsed.total_experience_years,
        confidence=parsed.confidence,
    )

    assert candidate.first_name == "John"
    assert candidate.last_name == "Smith"
    assert candidate.email == "john.smith@example.com"
    assert candidate.current_title == "Senior Engineer"
    assert candidate.current_company == "Acme Corp"
    # Re-open simulation: already-filled fields are not overwritten by a re-parse.
    candidate.first_name = "John"
    candidate.current_title = "Senior Engineer"
    _fill_candidate(
        candidate,
        {
            "full_name": "Professional Summary",
            "email": "other@example.com",
            "experience": [{"title": "Projects", "company": "Mumbai Port"}],
        },
        None,
        confidence={"name": 0.9, "email": 0.95, "title": 0.9, "company": 0.9},
    )
    assert candidate.first_name == "John"
    assert candidate.email == "john.smith@example.com"
    assert candidate.current_title == "Senior Engineer"


def test_fill_candidate_skips_low_confidence_wrong_values() -> None:
    candidate = _empty_candidate()
    _fill_candidate(
        candidate,
        {
            "full_name": "Professional Summary",
            "email": "john.smith@example.com",
            "location": "Mumbai",
            "experience": [{"title": "Projects", "company": "Mumbai Port Digitization"}],
        },
        None,
        confidence={
            "name": 0.2,
            "email": 0.95,
            "location": 0.3,
            "title": 0.2,
            "company": 0.2,
        },
    )
    assert candidate.first_name == ""
    assert candidate.last_name == ""
    assert candidate.email == "john.smith@example.com"
    assert candidate.current_location == ""
    assert candidate.current_title == ""
    assert candidate.current_company == ""
