from app.cv_engine.extract import extract_text
from app.cv_engine.parser import RuleBasedParser, merge_experience_years, segment_sections
from datetime import date


SAMPLE = """
Jane Doe
jane.doe@example.com | +1 555 123 4567 | https://linkedin.com/in/janedoe
Bengaluru, India

Summary
Backend engineer with fintech experience.

Experience
Senior Backend Engineer
Acme Payments
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


def test_extract_pdf_from_generated_sample() -> None:
    from pathlib import Path

    pdf = Path(__file__).resolve().parents[1] / "golden" / "cvs" / "cv01_backend.pdf"
    if not pdf.exists():
        result = extract_text(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n", "pdf")
        assert isinstance(result.text, str)
        return
    result = extract_text(pdf.read_bytes(), "application/pdf")
    assert "priya.sharma@example.com" in result.text.lower() or len(result.text) > 50
