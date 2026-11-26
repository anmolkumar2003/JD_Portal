"""Small helpers shared by the extractors."""

from __future__ import annotations

import re

from app.cv_engine.quick_fill.data import get_rules
from app.cv_engine.quick_fill.types import Alternative, Confidence, FieldResult, Json


def found(
    field: str,
    value: Json,
    display: str,
    confidence: Confidence,
    reason: str,
    *,
    candidates: list[Alternative] | None = None,
    warning: str | None = None,
) -> FieldResult:
    return FieldResult(
        field=field,
        value=value,
        display=display,
        confidence=confidence,
        reason=reason,
        candidates=candidates or [],
        warning=warning,
    )


def ambiguous(
    field: str, candidates: list[Alternative], warning: str, reason: str = ""
) -> FieldResult:
    """Several readings and no safe choice: no value, the candidates and a warning instead."""
    return FieldResult(
        field=field,
        value=None,
        display=None,
        confidence="low",
        reason=reason or "More than one possible value; nothing was guessed.",
        candidates=candidates,
        warning=warning,
    )


_LOWER_JOINERS = frozenset({"of", "and", "the", "for", "in", "at", "to"})


def tidy_words(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" \t\n,;:.-|/")


def smart_title(text: str) -> str:
    """ "senior java developer" -> "Senior Java Developer"; keeps QA, HR, DevOps, iOS as they are."""
    acronyms = get_rules().title_acronyms
    words = tidy_words(text).split(" ")
    out: list[str] = []
    for index, word in enumerate(words):
        low = word.casefold().strip(".")
        if low in acronyms:
            out.append(acronyms[low])
        elif index > 0 and low in _LOWER_JOINERS:
            out.append(low)
        elif word.islower() or (word.isupper() and len(word) > 3):
            out.append(word[:1].upper() + word[1:].lower())
        else:
            out.append(word)
    return " ".join(out)


def title_name(token: str) -> str:
    """Capitalise a name part: "rahul" -> "Rahul", "D'SOUZA" -> "D'Souza", "McDonald" unchanged."""
    if not (token.islower() or token.isupper()):
        return token
    parts = re.split(r"(['-])", token)
    return "".join(p[:1].upper() + p[1:].lower() if p not in ("'", "-") else p for p in parts)


def snippet(text: str, limit: int = 60) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    return flat if len(flat) <= limit else flat[: limit - 3] + "..."
