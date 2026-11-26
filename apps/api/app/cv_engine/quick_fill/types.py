"""Result types for Quick fill. Plain dataclasses: no FastAPI, no pydantic."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Literal, TypeAlias

Json: TypeAlias = str | int | float | bool | list["Json"] | dict[str, "Json"] | None
Confidence = Literal["high", "medium", "low"]

# Every field name the engine can return. The API and the web form use the same names.
FIELD_NAMES: tuple[str, ...] = (
    "first_name",
    "last_name",
    "email",
    "phone",
    "current_location",
    "current_company",
    "current_title",
    "total_experience_years",
    "notice_period_days",
    "current_ctc",
    "expected_ctc",
    "offered_ctc",
    "current_ctc_negotiable",
    "expected_ctc_negotiable",
    "offered_ctc_negotiable",
    "skills",
    "linkedin_url",
    "portfolio_url",
    "source",
    "tags",
    "department_hint",
    "job_hint",
)


@dataclass(frozen=True, slots=True)
class Alternative:
    """One possible value for a field the text left ambiguous."""

    value: Json
    display: str
    reason: str


@dataclass(slots=True)
class FieldResult:
    """One extracted field.

    `value` is None when the text was ambiguous (or the value is unknown): the possible readings
    are in `candidates` and `warning` says why nothing was guessed.
    """

    field: str
    value: Json = None
    display: str | None = None
    confidence: Confidence = "low"
    reason: str = ""
    candidates: list[Alternative] = dataclasses.field(default_factory=list)
    warning: str | None = None


@dataclass(slots=True)
class QuickFillResult:
    fields: list[FieldResult] = dataclasses.field(default_factory=list)
    warnings: list[str] = dataclasses.field(default_factory=list)
    # True when the text looks like several people. Nothing is extracted then (never mixed);
    # `segments` holds the pieces to extract one at a time, when they can be told apart.
    multiple_candidates: bool = False
    segments: list[str] = dataclasses.field(default_factory=list)
    # Short pieces of the input that no rule understood (shown so HR can see what was skipped).
    ignored: list[str] = dataclasses.field(default_factory=list)
    truncated: bool = False

    def get(self, name: str) -> FieldResult | None:
        for item in self.fields:
            if item.field == name:
                return item
        return None

    def value(self, name: str) -> Json:
        item = self.get(name)
        return item.value if item is not None else None
