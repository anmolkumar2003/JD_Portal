#!/usr/bin/env python3
"""Report parser precision/recall against golden labels. CV-03 quality harness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.cv_engine.parser import RuleBasedParser  # noqa: E402

CVS = Path(__file__).parent / "cvs"
LABELS = Path(__file__).parent / "labels"


def main() -> int:
    parser = RuleBasedParser()
    email_ok = phone_ok = 0
    skill_tp = skill_fp = skill_fn = 0
    years_ok = 0
    n = 0

    for label_path in sorted(LABELS.glob("*.json")):
        stem = label_path.stem
        cv_path = CVS / f"{stem}.txt"
        if not cv_path.exists():
            print(f"missing cv for {stem}")
            continue
        label = json.loads(label_path.read_text(encoding="utf-8"))
        parsed = parser.parse(cv_path.read_text(encoding="utf-8"))
        n += 1

        if parsed.email and parsed.email.lower() == label["email"].lower():
            email_ok += 1
        if parsed.phone and label.get("phone_contains", "") in (parsed.phone or ""):
            phone_ok += 1

        predicted = {s.lower() for s in parsed.skills}
        gold = {s.lower() for s in label.get("skills", [])}
        skill_tp += len(predicted & gold)
        skill_fp += len(predicted - gold)
        skill_fn += len(gold - predicted)

        if parsed.total_experience_years is not None and parsed.total_experience_years >= label.get(
            "min_experience_years", 0
        ):
            years_ok += 1

        print(
            f"{stem}: email={parsed.email!r} phone={parsed.phone!r} "
            f"skills={len(parsed.skills)} years={parsed.total_experience_years}"
        )

    precision = skill_tp / (skill_tp + skill_fp) if (skill_tp + skill_fp) else 0.0
    recall = skill_tp / (skill_tp + skill_fn) if (skill_tp + skill_fn) else 0.0
    print("---")
    print(f"samples={n}")
    print(f"email_accuracy={email_ok / n if n else 0:.2%}")
    print(f"phone_accuracy={phone_ok / n if n else 0:.2%}")
    print(f"skills_precision={precision:.2%}")
    print(f"skills_recall={recall:.2%}")
    print(f"experience_years_ok={years_ok / n if n else 0:.2%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
