"""Request/response schemas for POST /candidates/quick-parse (extract only, nothing is stored)."""

from typing import Literal

from pydantic import BaseModel, JsonValue

# The text limit is checked in the service (not as a pydantic constraint) so an over-long,
# personal text is never echoed back inside a validation error.
QUICK_PARSE_MAX_CHARS = 2000


class QuickParseIn(BaseModel):
    text: str


class QuickParseCandidateOut(BaseModel):
    value: JsonValue
    display: str
    reason: str


class QuickParseFieldOut(BaseModel):
    field: str
    value: JsonValue
    display: str | None
    confidence: Literal["high", "medium", "low"]
    reason: str
    candidates: list[QuickParseCandidateOut]
    warning: str | None


class QuickParseOut(BaseModel):
    fields: list[QuickParseFieldOut]
    warnings: list[str]
    multiple_candidates: bool
    segments: list[str]
    ignored: list[str]
    truncated: bool
