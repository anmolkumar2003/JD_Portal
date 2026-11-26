"""Regression floors for the hand-labelled fixtures (see scripts/quick_fill_accuracy.py).

The numbers are floors, not goals: they stop a rule change from silently making Quick fill worse.
"""

from __future__ import annotations

from app.cv_engine.quick_fill.evaluate import FIXTURE, HOLDOUT, evaluate, load_fixture


def test_fixtures_have_the_expected_size() -> None:
    assert len(load_fixture(FIXTURE)) == 50
    assert len(load_fixture(HOLDOUT)) == 20


def test_fifty_line_fixture_accuracy() -> None:
    report = evaluate(FIXTURE)
    total = report.total()

    assert total.accuracy is not None and total.accuracy >= 0.97
    assert total.high_precision is not None and total.high_precision >= 0.99
    assert report.multi_ok == report.multi_total


def test_holdout_accuracy() -> None:
    total = evaluate(HOLDOUT).total()

    assert total.accuracy is not None and total.accuracy >= 0.93
    assert total.high_precision is not None and total.high_precision >= 0.99


def test_nothing_is_guessed_for_fields_expected_to_stay_empty() -> None:
    """A spurious value or a wrong one is worse than a missed one: both must stay at zero."""
    for path in (FIXTURE, HOLDOUT):
        total = evaluate(path).total()

        assert total.spurious == 0, path.name
        assert total.wrong == 0, path.name


def test_no_field_is_wrong_with_high_confidence() -> None:
    for path in (FIXTURE, HOLDOUT):
        for name, score in evaluate(path).fields.items():
            assert score.high_total == score.high_correct, f"{path.name}: {name}"
