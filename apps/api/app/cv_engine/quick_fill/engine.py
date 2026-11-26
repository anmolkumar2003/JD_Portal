"""Quick fill entry point: free text in, normalized fields with confidence out."""

from __future__ import annotations

from app.cv_engine.quick_fill.types import QuickFillResult

MAX_CHARS = 2000


def parse_quick_fill(text: str) -> QuickFillResult:
    """Extract candidate fields from pasted text. Pure function: stores and logs nothing."""
    result = QuickFillResult()
    if not text.strip():
        result.warnings.append("Nothing to extract: the text is empty.")
    return result
