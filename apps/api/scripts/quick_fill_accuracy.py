"""Quick fill accuracy report over the 50-line fixture.

Run from apps/api:  python -m scripts.quick_fill_accuracy [--fixture PATH] [--no-details]
Exit code 1 when overall accuracy drops below --min-accuracy (default 0: report only).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.cv_engine.quick_fill.evaluate import FIXTURE, HOLDOUT, evaluate, format_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        action="append",
        help="default: the 50-line set and the hold-out set",
    )
    parser.add_argument("--no-details", action="store_true", help="hide the list of mismatches")
    parser.add_argument("--min-accuracy", type=float, default=0.0)
    args = parser.parse_args()
    worst = 1.0
    for path in args.fixture or [FIXTURE, HOLDOUT]:
        report = evaluate(path)
        print(f"== {path.name}")
        print(format_report(report, show_mismatches=not args.no_details))
        print()
        worst = min(worst, report.total().accuracy or 0.0)
    return 0 if worst >= args.min_accuracy else 1


if __name__ == "__main__":
    sys.exit(main())
