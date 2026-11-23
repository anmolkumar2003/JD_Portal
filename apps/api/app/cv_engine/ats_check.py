"""ATS-friendliness checklist A1–A12. CV-04 / Part 8.1."""

from __future__ import annotations

import re
from typing import Any

from app.cv_engine.parser import DATE_RANGE_RE, EMAIL_RE, PHONE_RE, segment_sections
from app.cv_engine.skills import find_skills_in_text
from app.cv_engine.types import AtsCheckItem, AtsResult, ExtractResult, ParsedCV

ENGINE_VERSION = "ats-1.0"

CHECKS_SPEC: list[dict[str, Any]] = [
    {
        "id": "A1",
        "label": "Text is extractable (not image-only PDF)",
        "weight": 15,
        "suggestion": "Export as a text-based PDF or DOCX",
    },
    {
        "id": "A2",
        "label": "Standard file type (PDF/DOCX) and under 5 MB",
        "weight": 5,
        "suggestion": "Use PDF or DOCX",
    },
    {
        "id": "A3",
        "label": "Contact info parsed (name, email, phone)",
        "weight": 10,
        "suggestion": "Put contact details in the body, not the header/footer",
    },
    {
        "id": "A4",
        "label": "Standard section headings found (Experience, Education, Skills)",
        "weight": 15,
        "suggestion": "Use conventional headings",
    },
    {
        "id": "A5",
        "label": "No multi-column or table layout detected",
        "weight": 10,
        "suggestion": "Use a single-column layout",
    },
    {
        "id": "A6",
        "label": "No text boxes, images holding text, or key info in headers/footers",
        "weight": 8,
        "suggestion": "Move content into the main body",
    },
    {
        "id": "A7",
        "label": "Dates consistently formatted and parseable",
        "weight": 7,
        "suggestion": 'Use "MMM YYYY – MMM YYYY"',
    },
    {
        "id": "A8",
        "label": "Work history has title, company and dates per role",
        "weight": 10,
        "suggestion": "List title, company, dates on separate clear lines",
    },
    {
        "id": "A9",
        "label": "Skills section present with recognizable skills",
        "weight": 7,
        "suggestion": "Add a dedicated Skills section",
    },
    {
        "id": "A10",
        "label": "Reasonable length (1–4 pages)",
        "weight": 5,
        "suggestion": "Trim or condense",
    },
    {
        "id": "A11",
        "label": "No unusual characters, excessive graphics, icons as bullets",
        "weight": 4,
        "suggestion": "Use standard bullets and fonts",
    },
    {
        "id": "A12",
        "label": "Parse completeness (share of expected fields extracted)",
        "weight": 4,
        "suggestion": "Simplify the layout",
    },
]


def _band(score: int) -> str:
    if score >= 80:
        return "good"
    if score >= 60:
        return "needs_improvement"
    return "poor"


def _multi_column_heuristic(text: str) -> bool:
    """Rough signal: many lines with large mid-line gaps or pipe tables."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False
    wide_gap = sum(1 for ln in lines if re.search(r"\S {6,}\S", ln))
    pipes = sum(1 for ln in lines if ln.count("|") >= 2)
    return (wide_gap / max(len(lines), 1)) > 0.25 or (pipes / max(len(lines), 1)) > 0.15


def _unusual_chars(text: str) -> bool:
    if not text:
        return True
    weird = sum(1 for ch in text if ord(ch) > 127 and ch not in "–—•·éñüöäà")
    return (weird / max(len(text), 1)) > 0.02


def run_ats_check(
    *,
    extracted: ExtractResult,
    parsed: ParsedCV,
    mime_type: str | None = None,
) -> AtsResult:
    text = extracted.text or ""
    sections = segment_sections(text)
    items: list[AtsCheckItem] = []

    # A1
    a1 = len(text) >= 200 and not (extracted.ocr_used and len(text) < 400)
    items.append(
        AtsCheckItem(
            id="A1",
            label=CHECKS_SPEC[0]["label"],
            passed=a1,
            weight=15,
            detail=f"Extracted {len(text)} characters via {extracted.method}",
            suggestion=CHECKS_SPEC[0]["suggestion"],
        )
    )

    # A2
    mime = (mime_type or "").lower()
    ok_type = mime in {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "",
    } or extracted.method in {"pdfplumber", "pymupdf", "python-docx", "tesseract"}
    a2 = ok_type and extracted.file_size <= 5 * 1024 * 1024
    items.append(
        AtsCheckItem(
            id="A2",
            label=CHECKS_SPEC[1]["label"],
            passed=a2,
            weight=5,
            detail=f"size={extracted.file_size} method={extracted.method}",
            suggestion=CHECKS_SPEC[1]["suggestion"],
        )
    )

    # A3
    contact_hits = sum(
        [
            bool(parsed.full_name),
            bool(parsed.email or EMAIL_RE.search(text)),
            bool(parsed.phone or PHONE_RE.search(text)),
        ]
    )
    a3 = contact_hits >= 2
    items.append(
        AtsCheckItem(
            id="A3",
            label=CHECKS_SPEC[2]["label"],
            passed=a3,
            weight=10,
            detail=f"contact_fields={contact_hits}/3",
            suggestion=CHECKS_SPEC[2]["suggestion"],
        )
    )

    # A4
    needed = {"experience", "education", "skills"}
    found = needed.intersection(parsed.sections_found or sections.keys())
    a4 = len(found) >= 2
    items.append(
        AtsCheckItem(
            id="A4",
            label=CHECKS_SPEC[3]["label"],
            passed=a4,
            weight=15,
            detail=f"sections={sorted(found)}",
            suggestion=CHECKS_SPEC[3]["suggestion"],
        )
    )

    # A5
    a5 = not _multi_column_heuristic(text)
    items.append(
        AtsCheckItem(
            id="A5",
            label=CHECKS_SPEC[4]["label"],
            passed=a5,
            weight=10,
            detail="multi-column heuristic",
            suggestion=CHECKS_SPEC[4]["suggestion"],
        )
    )

    # A6
    a6 = not extracted.ocr_used
    items.append(
        AtsCheckItem(
            id="A6",
            label=CHECKS_SPEC[5]["label"],
            passed=a6,
            weight=8,
            detail="ocr_used" if extracted.ocr_used else "text_layer_present",
            suggestion=CHECKS_SPEC[5]["suggestion"],
        )
    )

    # A7
    ranges = list(DATE_RANGE_RE.finditer(text))
    a7 = len(ranges) >= 1
    items.append(
        AtsCheckItem(
            id="A7",
            label=CHECKS_SPEC[6]["label"],
            passed=a7,
            weight=7,
            detail=f"date_ranges={len(ranges)}",
            suggestion=CHECKS_SPEC[6]["suggestion"],
        )
    )

    # A8
    roles_ok = 0
    for exp in parsed.experience:
        if exp.title and (exp.company or exp.start_date):
            roles_ok += 1
    a8 = roles_ok >= 1
    items.append(
        AtsCheckItem(
            id="A8",
            label=CHECKS_SPEC[7]["label"],
            passed=a8,
            weight=10,
            detail=f"roles_with_structure={roles_ok}",
            suggestion=CHECKS_SPEC[7]["suggestion"],
        )
    )

    # A9
    skill_section = "skills" in (parsed.sections_found or [])
    skills = parsed.skills or find_skills_in_text(sections.get("skills", ""))
    a9 = skill_section and len(skills) >= 3
    items.append(
        AtsCheckItem(
            id="A9",
            label=CHECKS_SPEC[8]["label"],
            passed=a9,
            weight=7,
            detail=f"skills={len(skills)} section={skill_section}",
            suggestion=CHECKS_SPEC[8]["suggestion"],
        )
    )

    # A10
    pages = extracted.page_count or max(1, len(text) // 3000)
    a10 = 1 <= pages <= 4
    items.append(
        AtsCheckItem(
            id="A10",
            label=CHECKS_SPEC[9]["label"],
            passed=a10,
            weight=5,
            detail=f"pages≈{pages}",
            suggestion=CHECKS_SPEC[9]["suggestion"],
        )
    )

    # A11
    a11 = not _unusual_chars(text)
    items.append(
        AtsCheckItem(
            id="A11",
            label=CHECKS_SPEC[10]["label"],
            passed=a11,
            weight=4,
            detail="character_set_check",
            suggestion=CHECKS_SPEC[10]["suggestion"],
        )
    )

    # A12
    expected = ["full_name", "email", "phone", "skills", "experience", "education"]
    present = 0
    if parsed.full_name:
        present += 1
    if parsed.email:
        present += 1
    if parsed.phone:
        present += 1
    if parsed.skills:
        present += 1
    if parsed.experience:
        present += 1
    if parsed.education:
        present += 1
    ratio = present / len(expected)
    a12 = ratio >= 0.5
    items.append(
        AtsCheckItem(
            id="A12",
            label=CHECKS_SPEC[11]["label"],
            passed=a12,
            weight=4,
            detail=f"fields={present}/{len(expected)}",
            suggestion=CHECKS_SPEC[11]["suggestion"],
        )
    )

    score = int(round(sum(i.weight for i in items if i.passed)))
    return AtsResult(score=score, band=_band(score), checks=items, engine_version=ENGINE_VERSION)  # type: ignore[arg-type]
