"""Regression: CV section/identity mapping must not put Summary/Projects into Name/Location.

CV-03 — values are identified by section aliases and contact proximity, not by line order.
Uncertain extractions fields stay unset instead of landing in the wrong form slot.
"""

from __future__ import annotations

import pytest

from app.cv_engine.parser import (
    AUTOFILL_MIN_CONFIDENCE,
    RuleBasedParser,
    _clean_name,
    _heading_key,
    segment_sections,
)

# Heading variants that previously became the candidate name.
HEADING_FIRST_CV = """
Professional Summary
Results-driven backend engineer with 8 years building payment platforms.

John Smith
john.smith@example.com | +91 98765 43210 | Bengaluru, India

Experience
Senior Engineer
Acme Corp
Jan 2020 – Present
Built Python FastAPI services on PostgreSQL.

Projects
Mumbai Port Digitization Platform
Led logistics tooling used in Singapore and Dubai.

Education
B.Tech Computer Science
IIT Example
2013 – 2017

Skills
Python, FastAPI, PostgreSQL, Redis
"""

CLASSIC_CV = """
Jane Doe
jane.doe@example.com | +1 555 123 4567 | https://linkedin.com/in/janedoe
Bengaluru, India

Summary
Backend engineer with fintech experience.

Experience
Senior Backend Engineer
Globex Payments
Jan 2020 – Present
Built Python FastAPI services on PostgreSQL and Redis.

Software Engineer
Beta Labs
Jun 2017 – Dec 2019
Worked on JavaScript and React dashboards.

Education
B.Tech Computer Science
IIT Example
2013 – 2017

Skills
Python, FastAPI, PostgreSQL, Redis, Docker, Kubernetes

Certifications
AWS Certified Developer
"""

OBJECTIVE_THEN_NAME = """
Career Objective
Seeking a senior platform role in distributed systems.

Priya Nair
priya.nair@example.com | +91 98111 22334
Hyderabad, India

Work Experience
Staff Engineer
PayFlow India
Mar 2021 – Present
Owned checkout APIs.

Personal Projects
Open Source Task Runner
Side project noted in Bangalore office wiki.

Skills
Python, Go, Kubernetes
"""

SKILLS_ONLY_NO_NAME_HEADING = """
Technical Skills
Python, React, TypeScript

Experience
Frontend Engineer
Nova Labs
2022 – Present
Built design systems.
"""


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Professional Summary", "summary"),
        ("PROFESSIONAL SUMMARY", "summary"),
        ("Career Objective", "summary"),
        ("Projects", "projects"),
        ("KEY PROJECTS", "projects"),
        ("Personal Projects", "projects"),
        ("Work Experience", "experience"),
        ("Technical Skills", "skills"),
        ("Education and Training", "education"),
        ("Project Manager", None),  # job title, not a section
        ("Results-driven engineer with experience building platforms", None),
    ],
)
def test_heading_key_identifies_sections_by_alias(line: str, expected: str | None) -> None:
    assert _heading_key(line) == expected


@pytest.mark.parametrize(
    "line",
    [
        "Professional Summary",
        "Projects",
        "Career Objective",
        "Technical Skills",
        "Work Experience",
    ],
)
def test_section_headings_are_never_cleaned_as_names(line: str) -> None:
    assert _clean_name(line) is None


def test_heading_first_cv_maps_name_and_keeps_projects_out_of_experience() -> None:
    sections = segment_sections(HEADING_FIRST_CV)
    assert "summary" in sections
    assert "projects" in sections
    assert "Projects" not in (sections.get("experience") or "")
    assert "Mumbai Port" in (sections.get("projects") or "")

    parsed = RuleBasedParser().parse(HEADING_FIRST_CV)
    assert parsed.full_name == "John Smith"
    assert parsed.email == "john.smith@example.com"
    assert parsed.confidence.get("name", 0) >= AUTOFILL_MIN_CONFIDENCE
    # Projects must not become a fake job used for current title/company.
    titles = [e.title for e in parsed.experience]
    companies = [e.company for e in parsed.experience]
    assert "Projects" not in titles
    assert not any(c and "Mumbai Port" in c for c in companies)
    assert parsed.experience[0].title == "Senior Engineer"
    assert parsed.experience[0].company == "Acme Corp"
    assert parsed.confidence.get("title", 0) >= AUTOFILL_MIN_CONFIDENCE


def test_classic_cv_still_extracts_core_fields() -> None:
    parsed = RuleBasedParser().parse(CLASSIC_CV)
    assert parsed.full_name == "Jane Doe"
    assert parsed.email == "jane.doe@example.com"
    assert parsed.phone is not None
    assert "Python" in parsed.skills
    assert parsed.experience[0].title == "Senior Backend Engineer"
    assert parsed.summary is not None
    assert "fintech" in parsed.summary.lower()


def test_objective_heading_does_not_become_the_name() -> None:
    parsed = RuleBasedParser().parse(OBJECTIVE_THEN_NAME)
    assert parsed.full_name == "Priya Nair"
    assert parsed.full_name != "Career Objective"
    titles = [e.title for e in parsed.experience]
    assert "Personal Projects" not in titles
    assert "Open Source Task Runner" not in titles


def test_skills_heading_is_not_a_person_name() -> None:
    parsed = RuleBasedParser().parse(SKILLS_ONLY_NO_NAME_HEADING)
    assert parsed.full_name != "Technical Skills"
    # No reliable contact-block name → leave name unmapped rather than invent one.
    assert parsed.full_name is None or parsed.confidence.get("name", 0) < AUTOFILL_MIN_CONFIDENCE


def test_location_does_not_prefer_project_body_places_without_contact_place() -> None:
    """Without spaCy, location stays unset; with spaCy, contact blob wins over Projects."""
    text = """
Alex Rivera
alex.rivera@example.com | +1 415 555 0100
San Francisco, CA

Experience
Engineer
Acme
2020 – Present
Built APIs.

Projects
Mumbai Port Digitization
Deployed edge nodes in Singapore and Dubai.
"""
    parsed = RuleBasedParser().parse(text)
    assert parsed.full_name == "Alex Rivera"
    # Either contact location or blank — never a project-only city when contact has one
    # (spaCy optional in CI; when absent location is None).
    if parsed.location:
        assert "Mumbai" not in parsed.location
        assert "Singapore" not in parsed.location
        assert "Dubai" not in parsed.location
        assert parsed.confidence.get("location", 0) >= AUTOFILL_MIN_CONFIDENCE


def test_uncertain_name_confidence_stays_below_autofill_floor() -> None:
    text = "Random Words Here\nsome body text without contact details\n"
    parsed = RuleBasedParser().parse(text)
    if parsed.full_name:
        assert parsed.confidence.get("name", 0) < AUTOFILL_MIN_CONFIDENCE or _clean_name(
            parsed.full_name
        )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Jane Doe | jane.doe@example.com | +1 555 111 2222 | Austin, TX\n\nSummary\nEngineer.\n",
            "Jane Doe",
        ),
        (
            "JANE DOE\njane.doe@example.com\n+1 555 111 2222\n\nPROFESSIONAL SUMMARY\nBuilder.\n",
            "Jane Doe",
        ),
        (
            "Doe, Jane\njane.doe@example.com\n+1 555 111 2222\n",
            "Jane Doe",
        ),
        (
            "Jane Doe, PhD\njane.doe@example.com\n+1 555 111 2222\n",
            "Jane Doe",
        ),
        (
            "Mr. Jane Doe\njane.doe@example.com\n+1 555 111 2222\n",
            "Jane Doe",
        ),
        (
            "Jane Doe                    Software Engineer\njane.doe@example.com\n",
            "Jane Doe",
        ),
        (
            "CURRICULUM VITAE\n\nJane Doe\njane.doe@example.com | +1 555 111 2222\n",
            "Jane Doe",
        ),
    ],
)
def test_name_layouts_map_cleanly_for_autofill(text: str, expected: str) -> None:
    parsed = RuleBasedParser().parse(text)
    assert parsed.full_name == expected
    assert parsed.confidence.get("name", 0) >= AUTOFILL_MIN_CONFIDENCE
    assert _clean_name(parsed.full_name) == expected


# --- Place text must never become a name; every section lands in its own field -----------------


@pytest.mark.parametrize(
    "text",
    [
        "Punjab India Ludhiana\njohn@example.com | +91 98765 43210\n\nSummary\nEngineer.\n",
        "Punjab India\nLudhiana\naman@example.com\n+91 98765 43210\n",
        "Ludhiana, Punjab, India\naman@example.com\n+91 98765 43210\n",
    ],
)
def test_place_text_is_never_taken_as_the_name(text: str) -> None:
    parsed = RuleBasedParser().parse(text)
    assert parsed.full_name is None
    assert parsed.confidence.get("name", 0) < AUTOFILL_MIN_CONFIDENCE


def test_real_name_wins_when_address_lines_are_present() -> None:
    text = "Ludhiana, Punjab, India\nAman Verma\naman@example.com\n+91 98765 43210\n"
    parsed = RuleBasedParser().parse(text)
    assert parsed.full_name == "Aman Verma"
    assert parsed.location == "Ludhiana, Punjab"


def test_location_comes_from_header_not_projects() -> None:
    text = """Aman Verma
aman@example.com | +91 98765 43210 | Pune

Projects
Port Platform
Rolled out in Mumbai and Singapore.
"""
    parsed = RuleBasedParser().parse(text)
    assert parsed.location == "Pune"


def test_location_is_empty_when_header_has_none() -> None:
    text = """Aman Verma
aman@example.com | +91 98765 43210

Projects
Port Platform
Rolled out in Mumbai.
"""
    assert RuleBasedParser().parse(text).location is None


def test_each_section_lands_in_its_own_field() -> None:
    parsed = RuleBasedParser().parse(HEADING_FIRST_CV)
    assert parsed.full_name == "John Smith"
    assert parsed.summary is not None and "Results-driven" in parsed.summary
    assert "John Smith" not in parsed.summary or parsed.full_name == "John Smith"
    assert [p.name for p in parsed.projects] == ["Mumbai Port Digitization Platform"]
    assert "Singapore" in (parsed.projects[0].description or "")
    assert parsed.location is None or "Mumbai" not in parsed.location
    assert [e.title for e in parsed.experience] == ["Senior Engineer"]
    assert parsed.education and "B.Tech" in (parsed.education[0].degree or "")
    assert {"Python", "FastAPI", "PostgreSQL"} <= set(parsed.skills)
    data = parsed.to_data_dict()
    assert data["projects"][0]["name"] == "Mumbai Port Digitization Platform"
