"""Quick fill: pull candidate fields out of pasted free text (rules, dictionaries, spaCy NER).

Pure Python package (no FastAPI imports). It never stores or logs the text it is given.
"""

from app.cv_engine.quick_fill.engine import MAX_CHARS, parse_quick_fill
from app.cv_engine.quick_fill.types import (
    FIELD_NAMES,
    Alternative,
    Confidence,
    FieldResult,
    Json,
    QuickFillResult,
)

__all__ = [
    "FIELD_NAMES",
    "MAX_CHARS",
    "Alternative",
    "Confidence",
    "FieldResult",
    "Json",
    "QuickFillResult",
    "parse_quick_fill",
]
