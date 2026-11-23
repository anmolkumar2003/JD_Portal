from datetime import date

from app.cv_engine.extract import extract_text
from app.cv_engine.parser import RuleBasedParser, merge_experience_years, segment_sections

SAMPLE = """
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


def test_segment_sections() -> None:
    sections = segment_sections(SAMPLE)
    assert "experience" in sections
    assert "skills" in sections
    assert "education" in sections


def test_merge_overlap_years() -> None:
    ranges = [
        (date(2020, 1, 1), date(2022, 1, 1)),
        (date(2021, 1, 1), date(2023, 1, 1)),
    ]
    years = merge_experience_years(ranges)
    assert 2.5 <= years <= 3.5


def test_rule_based_parser_extracts_core_fields() -> None:
    parsed = RuleBasedParser().parse(SAMPLE)
    assert parsed.email == "jane.doe@example.com"
    assert parsed.phone is not None
    assert "Python" in parsed.skills
    assert parsed.total_experience_years is not None
    assert parsed.total_experience_years >= 4


def test_phone_keeps_trailing_digit_and_middle_dot_dates() -> None:
    text = """
Priya Sharma
priya.sharma@example.com | +91 98111 22334

Summary
Senior backend engineer with 7 years building platforms.

Experience
Senior Software Engineer
PayFlow India
Mar 2021 · Present
Built Python FastAPI services.
"""
    parsed = RuleBasedParser().parse(text)
    assert parsed.phone == "+91 98111 22334"
    assert parsed.full_name == "Priya Sharma"
    assert parsed.total_experience_years is not None
    assert parsed.total_experience_years >= 7


def test_name_does_not_include_email_line() -> None:
    text = "Sara Ali\nsara.ali@example.com | +44 7700 900123\nLondon, UK\n\nSkills\nReact, TypeScript\n"
    parsed = RuleBasedParser().parse(text)
    assert parsed.full_name == "Sara Ali"
    assert parsed.phone == "+44 7700 900123"
    assert "@" not in (parsed.full_name or "")


def test_extract_pdf_from_generated_sample() -> None:
    from pathlib import Path

    pdf = Path(__file__).resolve().parents[1] / "golden" / "cvs" / "cv01_backend.pdf"
    if not pdf.exists():
        result = extract_text(
            b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n", "pdf"
        )
        assert isinstance(result.text, str)
        return
    result = extract_text(pdf.read_bytes(), "application/pdf")
    assert "priya.sharma@example.com" in result.text.lower() or len(result.text) > 50
