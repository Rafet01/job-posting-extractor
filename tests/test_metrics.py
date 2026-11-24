"""Metrics on hand-calculated examples: exact, title, set, skill and class scores."""

import pytest

from extractor.metrics import (
    classification_report, exact_match, location_prf, set_prf, skill_prf, text_match,
)


def test_exact_match_treats_two_missing_values_as_equal() -> None:
    """Missing scalar values match each other and differ from stated values."""
    assert exact_match(None, None)
    assert not exact_match(None, 0)
    assert not exact_match("required", "plus")


def test_title_match_depends_on_the_threshold() -> None:
    """This wording change scores below 0.85 but passes at 0.70."""
    assert text_match(None, "")
    assert not text_match("Data & AI Intern", "Data and AI Internship")
    assert text_match("Data & AI Intern", "Data and AI Internship", threshold=0.70)


def test_set_scores_follow_the_empty_set_conventions() -> None:
    """Exercise the empty and disjoint set conventions."""
    assert set_prf(set(), set()) == (1, 1, 1)
    assert set_prf({"x"}, set()) == (1, 0, 0)
    assert set_prf(set(), {"x"}) == (0, 1, 0)
    assert set_prf({"x"}, {"y"}) == (0, 0, 0)


def test_skill_alternatives_count_once_for_recall() -> None:
    """Alternatives count once for recall and individually for precision."""
    gold = ["python", "aws|azure|gcp"]
    assert skill_prf(gold, ["python", "azure", "gcp"]) == (1, 1, 1)
    assert skill_prf(gold, ["python", "r"]) == (0.5, 0.5, 0.5)
    assert skill_prf(["JS|TS"], ["TypeScript", "TS"]) == (1, 1, 1)
    assert skill_prf([], []) == (1, 1, 1)
    assert skill_prf(gold, []) == (1, 0, 0)
    assert skill_prf([], ["python"]) == (0, 1, 0)


def test_extra_skills_lower_precision_in_posting_001() -> None:
    """Four of eleven predicted skills satisfy both requirements."""
    pred = ["python", "r", "aws", "azure", "gcp", "llms", "snowflake",
            "databricks", "dataiku", "powerbi", "tableau"]
    assert skill_prf(["python", "aws|azure|gcp"], pred) == pytest.approx((4/11, 1, 8/15))


def test_locations_ignore_order_and_spelling() -> None:
    """Order and repeated place names have no effect."""
    assert location_prf(["Genève", "Zürich"], ["Zuerich", "Genf", "Geneva"]) == (1, 1, 1)


def test_macro_f1_includes_classes_seen_on_one_side_only() -> None:
    """Include classes appearing on only one side in the macro average."""
    report = classification_report(["a", "a", "a", "b", "c"], ["a", "a", "b", "b", "d"])
    # Three of five correct. A: P=2/2, R=2/3. B: P=1/2, R=1/1.
    # C has no predictions and D has no gold examples, so both have F1=0.
    assert report["accuracy"] == 3/5
    assert report["per_class"] == {
        "a": {"precision": 1, "recall": 2/3, "f1": 4/5, "support": 3},
        "b": {"precision": 1/2, "recall": 1, "f1": 2/3, "support": 1},
        "c": {"precision": 0, "recall": 0, "f1": 0, "support": 1},
        "d": {"precision": 0, "recall": 0, "f1": 0, "support": 0},
    }
    assert report["macro_f1"] == pytest.approx((4/5 + 2/3) / 4)
    with pytest.raises(ValueError):
        classification_report(["a"], [])
