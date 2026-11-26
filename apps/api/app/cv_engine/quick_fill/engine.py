"""Quick fill entry point: free text in, normalized fields with confidence out.

Pure Python (no FastAPI). The text is never stored or logged here. Each extractor reads the
same cleaned text; spans an extractor has used are "claimed" so a later one cannot reuse them
(a salary is not also a notice period, a place is not also a name).
"""

from __future__ import annotations

from collections.abc import Callable

from app.cv_engine.quick_fill import contact, misc, numbers, person, place
from app.cv_engine.quick_fill.common import snippet
from app.cv_engine.quick_fill.text import Doc
from app.cv_engine.quick_fill.types import FIELD_NAMES, FieldResult, QuickFillResult

MAX_CHARS = 2000
MAX_IGNORED = 8

Extractor = Callable[[Doc], list[FieldResult]]

# Order matters: self-describing things first (they claim their text), vague ones last.
_EXTRACTORS: tuple[Extractor, ...] = (
    contact.extract_email,
    contact.extract_urls,
    contact.extract_phone,
    misc.extract_tags,
    misc.extract_job,
    misc.extract_department,
    misc.extract_source,
    numbers.extract_salary,
    numbers.extract_notice,
    numbers.extract_experience,
    place.extract_company,
    place.extract_location,
    place.extract_title,
    person.extract_name,
    misc.extract_skills,
)


def _ignored_pieces(doc: Doc) -> list[str]:
    pieces: list[str] = []
    for chunk in doc.chunks:
        text = doc.text[chunk.start : chunk.end]
        if not any(ch.isalnum() for ch in text) or chunk.key == "ignore":
            continue
        # A chunk is reported only when no rule used any part of it.
        if not any(doc.seen[chunk.start : chunk.end]):
            pieces.append(snippet(text))
    return pieces[:MAX_IGNORED]


def parse_quick_fill(text: str) -> QuickFillResult:
    """Extract candidate fields from pasted text. Pure function: stores and logs nothing."""
    result = QuickFillResult()
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]
        result.truncated = True
        result.warnings.append(
            f"The text was longer than {MAX_CHARS} characters; the rest was ignored."
        )
    if not text.strip():
        result.warnings.append("Nothing to extract: the text is empty.")
        return result
    doc = Doc.from_raw(text)
    if not doc.text.strip() or not any(ch.isalnum() for ch in doc.text):
        result.warnings.append("No readable text found (only symbols or emoji).")
        return result
    by_field: dict[str, FieldResult] = {}
    for extractor in _EXTRACTORS:
        try:
            produced = extractor(doc)
        except Exception:  # noqa: BLE001 - one broken rule must not lose the others; text is PII
            result.warnings.append("A part of the text could not be read and was skipped.")
            continue
        for item in produced:
            by_field.setdefault(item.field, item)
    result.fields = [by_field[name] for name in FIELD_NAMES if name in by_field]
    for item in result.fields:
        if item.warning and item.warning not in result.warnings:
            result.warnings.append(item.warning)
    result.ignored = _ignored_pieces(doc)
    if not result.fields:
        result.warnings.append(
            "No fields were recognised. Try labels such as 'Name:', 'Exp:', 'Current CTC:'."
        )
    return result
