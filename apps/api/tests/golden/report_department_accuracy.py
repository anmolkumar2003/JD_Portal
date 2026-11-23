#!/usr/bin/env python3
"""Parse department golden CVs and score them against same-department job specs."""

from __future__ import annotations

import json
from pathlib import Path

from app.cv_engine.ats_check import run_ats_check
from app.cv_engine.extract import extract_text
from app.cv_engine.matcher import score_match
from app.cv_engine.parser import RuleBasedParser
from app.cv_engine.types import CandidateMatchInput, JobRequirements, SkillSpec
from tests.golden.build_department_cvs import DEPARTMENTS

OUT = Path(__file__).parent / "departments"
REPORT = Path(__file__).parent / "real" / "DEPARTMENT_ACCURACY.md"


def _specs(names: list[str]) -> list[SkillSpec]:
    return [SkillSpec(name=n) for n in names]


def job_for(meta: dict[str, object]) -> JobRequirements:
    skills = [str(s) for s in list(meta["skills"])]  # type: ignore[arg-type]
    return JobRequirements(
        title=str(meta["title"]),
        required_skills=_specs(skills[:3]),
        preferred_skills=_specs(skills[3:]),
        min_experience=3,
        max_experience=10,
    )


def evaluate_file(path: Path, slug: str, meta: dict[str, object]) -> dict[str, object]:
    raw = path.read_bytes()
    mime = (
        "application/pdf"
        if path.suffix == ".pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    extracted = extract_text(raw, mime)
    parsed = RuleBasedParser().parse(extracted.text, file_meta=extracted)
    ats = run_ats_check(extracted=extracted, parsed=parsed, mime_type=mime)
    candidate = CandidateMatchInput(
        skills=list(parsed.skills),
        titles=[e.title for e in parsed.experience if e.title],
        total_experience_years=parsed.total_experience_years,
        education_degrees=[e.degree for e in parsed.education if e.degree],
        certifications=[c.name for c in parsed.certifications if c.name],
        location=parsed.location,
    )
    match = score_match(job_for(meta), candidate)
    expected_skills = {str(s) for s in list(meta["skills"])}  # type: ignore[arg-type]
    found = set(parsed.skills)
    return {
        "file": path.name,
        "slug": slug,
        "parsed_name": parsed.full_name,
        "expected_name": meta["name"],
        "email": parsed.email,
        "phone": parsed.phone,
        "skills_found": len(found),
        "skills_expected": sorted(expected_skills),
        "skills_hit": sorted(expected_skills & found),
        "skills_miss": sorted(expected_skills - found),
        "exp_years": parsed.total_experience_years,
        "ats": ats.score,
        "match": match.overall_score,
        "ocr": extracted.ocr_used,
        "chars": len(extracted.text or ""),
    }


def main() -> None:
    rows: list[dict[str, object]] = []
    for slug, meta in DEPARTMENTS.items():
        for ext in (".pdf", ".docx"):
            path = OUT / f"{slug}{ext}"
            if path.exists():
                rows.append(evaluate_file(path, slug, meta))
    unusual_meta = {
        "name": "Jane Unusual",
        "title": "Engineer",
        "skills": ["Python", "Shopify", "Kotlin"],
    }
    for name in ("unusual_dates.pdf", "scanned_unusual.pdf"):
        path = OUT / name
        if path.exists():
            rows.append(evaluate_file(path, "unusual", unusual_meta))
    two_col = OUT / "two_column_shopify.pdf"
    if two_col.exists():
        rows.append(evaluate_file(two_col, "shopify", DEPARTMENTS["shopify"]))

    lines = [
        "# Department golden CV accuracy",
        "",
        "| File | Name | Email | Skills hit/exp | Exp yrs | ATS | Match | Misses | OCR |",
        "| ---- | ---- | ----- | -------------- | ------- | --- | ----- | ------ | --- |",
    ]
    for r in rows:
        name_ok = "OK" if r["parsed_name"] == r["expected_name"] else f"{r['parsed_name']!r}"
        hit = f"{len(r['skills_hit'])}/{len(r['skills_expected'])}"
        misses = ", ".join(r["skills_miss"]) or "—"
        lines.append(
            f"| {r['file']} | {name_ok} | {r['email']} | {hit} | {r['exp_years']} | "
            f"{r['ats']} | {r['match']} | {misses} | {r['ocr']} |"
        )
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(rows, indent=2, default=str))
    lines.append("```")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT.read_text())


if __name__ == "__main__":
    main()
