"""Scores the Quick fill engine against a hand-labelled fixture. Pure Python, no FastAPI.

Fixture line (JSON): {"id": 1, "text": "...", "expect": {"field": value | null}, "multiple": bool}

- A field listed with a value must be filled with that value.
- A field listed as null (or not listed at all) must stay empty: filling it is "spurious".
- Ambiguity is a pass for a field expected to stay empty: the engine returned candidates, not a guess.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from app.cv_engine.quick_fill import parse_quick_fill
from app.cv_engine.quick_fill.types import FIELD_NAMES, Json, QuickFillResult

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "tests" / "cv_engine" / "fixtures"
FIXTURE = FIXTURE_DIR / "quick_fill_50.jsonl"
# Written after the 50-line set was tuned and never used to tune the rules: the honest number.
HOLDOUT = FIXTURE_DIR / "quick_fill_holdout_20.jsonl"


@dataclass(slots=True)
class FieldScore:
    correct: int = 0
    wrong: int = 0  # filled with a different value than expected
    missed: int = 0  # expected a value, got nothing
    spurious: int = 0  # expected empty, but the engine filled it
    high_correct: int = 0
    high_total: int = 0  # filled with "high" confidence (right or wrong)
    expected: int = 0  # rows where a value was expected

    @property
    def accuracy(self) -> float | None:
        return self.correct / self.expected if self.expected else None

    @property
    def high_precision(self) -> float | None:
        return self.high_correct / self.high_total if self.high_total else None


@dataclass(slots=True)
class Mismatch:
    row: int
    text: str
    field: str
    kind: str  # wrong | missed | spurious
    expected: Json
    got: Json


@dataclass(slots=True)
class Report:
    rows: int = 0
    fields: dict[str, FieldScore] = field(default_factory=lambda: defaultdict(FieldScore))
    mismatches: list[Mismatch] = field(default_factory=list)
    multi_ok: int = 0
    multi_total: int = 0

    def total(self) -> FieldScore:
        out = FieldScore()
        for item in self.fields.values():
            out.correct += item.correct
            out.wrong += item.wrong
            out.missed += item.missed
            out.spurious += item.spurious
            out.high_correct += item.high_correct
            out.high_total += item.high_total
            out.expected += item.expected
        return out


def load_fixture(path: Path = FIXTURE) -> list[dict[str, Json]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [cast("dict[str, Json]", json.loads(line)) for line in lines if line.strip()]


def same(name: str, expected: Json, got: Json) -> bool:
    """Compares one field the way HR would: case-insensitive text, digits of a phone, sets of tags."""
    if name == "phone":
        return re.sub(r"\D", "", str(expected)) == re.sub(r"\D", "", str(got))
    if name in ("skills", "tags"):
        if not isinstance(expected, list) or not isinstance(got, list):
            return False
        return {str(x).casefold() for x in expected} == {str(x).casefold() for x in got}
    if isinstance(expected, dict) or isinstance(got, dict):
        if not isinstance(expected, dict) or not isinstance(got, dict):
            return False
        keys = ("amount", "currency", "unit")
        return all(str(expected.get(k)) == str(got.get(k)) for k in keys)
    if isinstance(expected, bool) or isinstance(got, bool):
        return expected is got
    if isinstance(expected, int | float) and isinstance(got, int | float):
        return abs(float(expected) - float(got)) < 1e-6
    return str(expected).casefold() == str(got).casefold()


def score_row(report: Report, row: dict[str, Json], result: QuickFillResult) -> None:
    row_id = int(cast("int", row["id"]))
    text = str(row["text"])
    expect = cast("dict[str, Json]", row.get("expect") or {})
    report.rows += 1
    if row.get("multiple"):
        report.multi_total += 1
        if result.multiple_candidates and not result.fields:
            report.multi_ok += 1
        else:
            report.mismatches.append(
                Mismatch(row_id, text, "(several candidates)", "missed", True, False)
            )
        return
    for name in FIELD_NAMES:
        want = expect.get(name)
        item = result.get(name)
        got = item.value if item is not None else None
        score = report.fields[name]
        if want is not None:
            score.expected += 1
        if got is not None and item is not None and item.confidence == "high":
            score.high_total += 1
        if want is None and got is None:
            continue
        if want is None:
            score.spurious += 1
            report.mismatches.append(Mismatch(row_id, text, name, "spurious", None, got))
        elif got is None:
            score.missed += 1
            report.mismatches.append(Mismatch(row_id, text, name, "missed", want, None))
        elif same(name, want, got):
            score.correct += 1
            if item is not None and item.confidence == "high":
                score.high_correct += 1
        else:
            score.wrong += 1
            report.mismatches.append(Mismatch(row_id, text, name, "wrong", want, got))


def evaluate(path: Path = FIXTURE) -> Report:
    report = Report()
    for row in load_fixture(path):
        score_row(report, row, parse_quick_fill(str(row["text"])))
    return report


def _pct(value: float | None) -> str:
    return "  n/a" if value is None else f"{value * 100:5.1f}%"


def format_report(report: Report, *, show_mismatches: bool = True) -> str:
    lines = [
        f"Quick fill accuracy over {report.rows} fixture lines",
        "",
        f"{'field':26} {'expect':>6} {'right':>5} {'wrong':>5} {'missed':>6} {'spur.':>5} {'accuracy':>9} {'high-prec':>10}",
    ]
    for name in FIELD_NAMES:
        s = report.fields.get(name)
        if s is None or (s.expected == 0 and s.spurious == 0 and s.high_total == 0):
            continue
        lines.append(
            f"{name:26} {s.expected:6} {s.correct:5} {s.wrong:5} {s.missed:6} {s.spurious:5} "
            f"{_pct(s.accuracy):>9} {_pct(s.high_precision):>10}"
        )
    t = report.total()
    lines.append("-" * 80)
    lines.append(
        f"{'ALL FIELDS':26} {t.expected:6} {t.correct:5} {t.wrong:5} {t.missed:6} {t.spurious:5} "
        f"{_pct(t.accuracy):>9} {_pct(t.high_precision):>10}"
    )
    lines.append(
        f"Several-people texts detected and not mixed: {report.multi_ok}/{report.multi_total}"
    )
    if show_mismatches and report.mismatches:
        lines += ["", "Mismatches:"]
        for m in report.mismatches:
            lines.append(f"  #{m.row} {m.field} [{m.kind}] expected={m.expected!r} got={m.got!r}")
            lines.append(f"      {m.text[:100]!r}")
    return "\n".join(lines)
