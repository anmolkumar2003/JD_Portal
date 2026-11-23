"""Shared helpers for candidate PDF/Excel exports (no PII in logs or audit diffs)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

# Spreadsheet formula injection: values starting with these are treated as formulas.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_spreadsheet_value(value: object) -> object:
    """Prefix dangerous leading characters so Excel/LibreOffice treat the cell as text."""
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal, bool)):
        return value
    text = str(value)
    if text and text[0] in _FORMULA_PREFIXES:
        return f"'{text}"
    return text


def format_ctc(
    amount: Decimal | None,
    currency: str | None,
    unit: str | None,
) -> str:
    if amount is None:
        return ""
    cur = (currency or "INR").upper()
    u = (unit or "pa").lower()
    unit_label = "pa" if u == "pa" else "pm"
    return f"{cur} {amount:,.2f} {unit_label}"


def profile_data(parsed: dict[str, Any] | None, corrected: dict[str, Any] | None) -> dict[str, Any]:
    base = dict(parsed or {})
    if corrected:
        base.update(corrected)
    return base


def top_skills(data: dict[str, Any], *, limit: int = 15) -> list[str]:
    raw = data.get("skills") or []
    out: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict):
            name = item.get("name") or item.get("skill")
            if isinstance(name, str) and name.strip():
                out.append(name.strip())
        if len(out) >= limit:
            break
    return out


def format_experience(data: dict[str, Any], *, limit: int = 5) -> list[str]:
    lines: list[str] = []
    for item in (data.get("experience") or [])[:limit]:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("role") or ""
        company = item.get("company") or item.get("organization") or ""
        dates = item.get("dates") or item.get("period") or ""
        parts = [p for p in (title, company, dates) if p]
        if parts:
            lines.append(" — ".join(str(p) for p in parts))
    return lines


def format_education(data: dict[str, Any], *, limit: int = 4) -> list[str]:
    lines: list[str] = []
    for item in (data.get("education") or [])[:limit]:
        if not isinstance(item, dict):
            continue
        degree = item.get("degree") or item.get("qualification") or ""
        school = item.get("institution") or item.get("school") or ""
        year = item.get("year") or item.get("end_year") or ""
        parts = [p for p in (degree, school, year) if p]
        if parts:
            lines.append(" — ".join(str(p) for p in parts))
    return lines


def filters_summary(filters: Any) -> dict[str, str]:
    """Human-readable filter snapshot for the Excel meta sheet (no free-text PII beyond q)."""
    if filters is None:
        return {}
    data = (
        filters.model_dump(mode="json", exclude_none=True) if hasattr(filters, "model_dump") else {}
    )
    out: dict[str, str] = {}
    for key, value in data.items():
        if value is None or value == "" or value == []:
            continue
        if key == "q":
            # Length only — search text may contain emails/phones.
            out["q"] = f"(set, {len(str(value))} chars)"
            continue
        if isinstance(value, list):
            out[key] = ", ".join(str(v) for v in value)
        else:
            out[key] = str(value)
    return out
