"""Comparing runs: paired changes, the sign test and the Markdown report."""

import sys
from pathlib import Path

import pandas as pd
import pytest

from extractor.compare import build_report, describe_change, main, paired_change, sign_test
from extractor.evaluate import detail_rows, output_path, summarize
from extractor.schema import JobPosting
from extractor.splits import DEV
from tests.factories import posting


def test_sign_test_calls_small_splits_chance() -> None:
    """Two-sided exact p-values: 2-0 or 5-1 is compatible with chance, 6-0 is not."""
    assert sign_test(0, 0) == sign_test(1, 1) == 1.0
    assert sign_test(2, 0) == 0.5
    assert sign_test(5, 1) == pytest.approx(14 / 64)
    assert sign_test(6, 0) == sign_test(0, 6) == pytest.approx(2 / 64)


def test_paired_change_matches_postings_by_id_and_ignores_ties() -> None:
    """001 went up, 002 went down, 003 stayed the same, although the rows are in a different order."""
    before = pd.DataFrame({"id": ["001", "002", "003"], "field": "start", "score": [0.0, 1.0, 0.5]})
    after = pd.DataFrame({"id": ["003", "002", "001"], "field": "start", "score": [0.5, 0.0, 1.0]})
    assert paired_change(before, after, "start") == (1, 1, 1.0)


def test_only_p_below_005_is_called_significant() -> None:
    """Small differences are labelled n.s. instead of being presented as wins."""
    assert describe_change(2, 0, 0.5) == "+2 / −0 (p=0.50, n.s.)"
    assert describe_change(6, 0, 0.03) == "+6 / −0 (p=0.03, **significant**)"


def evaluated(predictions: dict[str, JobPosting], version: int = 2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score predictions against two labelled postings, as evaluate.main would."""
    labels = {"001": posting(start="asap"), "002": posting()}
    details = detail_rows(labels, predictions, {"001": "en", "002": "de"})
    return details, summarize(details).assign(metric_version=version)


def test_report_shows_failures_scores_changes_and_languages() -> None:
    """Run v1 misses the start of 001 and fails on 002. Run v2 gets both right."""
    runs = {"a v1": evaluated({"001": posting()}),
            "a v2": evaluated({"001": posting(start="asap"), "002": posting()})}
    report = build_report(runs, [("a v1", "a v2")])
    assert "| a v1 | 1 |" in report and "| a v2 | 0 |" in report
    assert "| start | normalized exact (proxy) | 0.00 | 1.00 |" in report
    assert "| start | +2 / −0 (p=0.50, n.s.) |" in report
    assert "| a v1 | 0.00 | 0.00 | 0.00 | - |" in report
    assert "fr n=0" in report


def test_report_rejects_runs_scored_with_different_metric_versions() -> None:
    """Scores from different scoring rules are not comparable."""
    runs = {"a v1": evaluated({}, version=1), "a v2": evaluated({}, version=2)}
    with pytest.raises(SystemExit, match="different metric versions"):
        build_report(runs, [("a v1", "a v2")])


def test_dev_runs_are_named_on_the_command_line_and_paired_with_the_first(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """On the dev split the report compares each named run with the first and is written to outputs/dev."""
    monkeypatch.chdir(tmp_path)
    for prompt, predictions in (("v1", {"001": posting()}), ("v3", {"001": posting(start="asap"), "002": posting()})):
        details, summary = evaluated(predictions)
        for kind, frame in (("details", details), ("summary", summary)):
            path = output_path(kind, "demo:7b", prompt, DEV)
            path.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(path, index=False)
    monkeypatch.setattr(sys, "argv", ["compare", "--split", "dev", "--run", "demo:7b", "v1", "--run", "demo:7b", "v3"])

    main()

    report = Path("outputs/dev/comparison.md").read_text(encoding="utf-8")
    assert report.startswith("# Run comparison (dev split)")
    assert "| demo:7b v1 → demo:7b v3 |" in report


def test_dev_comparison_needs_named_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """The four published runs only exist on the test split, so dev asks which runs to compare."""
    monkeypatch.setattr(sys, "argv", ["compare", "--split", "dev"])
    with pytest.raises(SystemExit):
        main()
