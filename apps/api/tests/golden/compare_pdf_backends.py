#!/usr/bin/env python3
"""Score each available PDF text backend against the golden labels.

    python tests/golden/compare_pdf_backends.py

Used to check that replacing a PDF library does not lower extraction quality.
Backends that are not installed are skipped.
"""

from __future__ import annotations

import io
import json
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.cv_engine.parser import RuleBasedParser  # noqa: E402

GOLDEN = Path(__file__).parent
PDF_DIRS = (GOLDEN / "cvs", GOLDEN / "real")


def _pdfplumber(data: bytes) -> str:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _pypdf(data: bytes) -> str:
    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)


def _pypdfium2(data: bytes) -> str:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(data)
    try:
        return "\n".join(page.get_textpage().get_text_range() for page in document)
    finally:
        document.close()


BACKENDS: dict[str, Callable[[bytes], str]] = {
    "pdfplumber": _pdfplumber,
    "pypdf": _pypdf,
    "pypdfium2": _pypdfium2,
}


def _score(extract: Callable[[bytes], str]) -> dict[str, float]:
    parser = RuleBasedParser()
    totals = {"n": 0, "email": 0, "phone": 0, "years": 0, "tp": 0, "fp": 0, "fn": 0, "chars": 0}
    for label_path in sorted((GOLDEN / "labels").glob("*.json")):
        label = json.loads(label_path.read_text(encoding="utf-8"))
        for directory in PDF_DIRS:
            pdf = directory / f"{label_path.stem}.pdf"
            if not pdf.exists():
                continue
            text = extract(pdf.read_bytes())
            parsed = parser.parse(text)
            totals["n"] += 1
            totals["chars"] += len(text)
            totals["email"] += (parsed.email or "").lower() == label["email"].lower()
            totals["phone"] += label.get("phone_contains", "") in (parsed.phone or "")
            years = parsed.total_experience_years
            totals["years"] += years is not None and years >= label.get("min_experience_years", 0)
            predicted = {s.lower() for s in parsed.skills}
            gold = {s.lower() for s in label.get("skills", [])}
            totals["tp"] += len(predicted & gold)
            totals["fp"] += len(predicted - gold)
            totals["fn"] += len(gold - predicted)
    n = totals["n"] or 1
    tp, fp, fn = totals["tp"], totals["fp"], totals["fn"]
    return {
        "samples": totals["n"],
        "email": totals["email"] / n,
        "phone": totals["phone"] / n,
        "years": totals["years"] / n,
        "skill_precision": tp / (tp + fp) if tp + fp else 0.0,
        "skill_recall": tp / (tp + fn) if tp + fn else 0.0,
        "avg_chars": totals["chars"] / n,
    }


def main() -> int:
    print(f"{'backend':<11} samples email  phone  years  skill_p skill_r avg_chars")
    for name, extract in BACKENDS.items():
        try:
            result = _score(extract)
        except ImportError:
            print(f"{name:<11} (not installed)")
            continue
        print(
            f"{name:<11} {result['samples']:>7.0f} {result['email']:>6.0%} {result['phone']:>6.0%} "
            f"{result['years']:>6.0%} {result['skill_precision']:>7.0%} "
            f"{result['skill_recall']:>7.0%} {result['avg_chars']:>9.0f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
