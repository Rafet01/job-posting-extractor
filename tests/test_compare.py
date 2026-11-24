"""Paired comparisons between runs, checked by hand."""

import pandas as pd
import pytest

from extractor.compare import build_report, describe_change, paired_change, sign_test
from extractor.evaluate import detail_rows, summarize
from extractor.schema import JobPosting


def test_sign_test() -> None:
    """Small splits are compatible with chance; 6 of 6 is not."""
    assert sign_test(0, 0) == 1.0
    assert sign_test(1, 1) == 1.0
    assert sign_test(2, 0) == 0.5
    assert sign_test(5, 1) == pytest.approx(14 / 64)
    assert sign_test(6, 0) == pytest.approx(2 / 64)
    assert sign_test(0, 6) == sign_test(6, 0)


def test_paired_change() -> None:
    """Ties are not counted, and postings are matched by ID, not by row order."""
    before = pd.DataFrame({"id": ["001", "002", "003"], "field": "start", "score": [0.0, 1.0, 0.5]})
    after = pd.DataFrame({"id": ["003", "002", "001"], "field": "start", "score": [0.5, 0.0, 1.0]})
    assert paired_change(before, after, "start") == (1, 1, 1.0)
    assert describe_change(2, 0, 0.5) == "+2 / −0 (p=0.50, n.s.)"
    assert "significant" in describe_change(6, 0, 0.03)


def posting(**changes: object) -> JobPosting:
    """A small valid posting, optionally with replaced fields."""
    values = dict(company="Example", role_title="Intern", german_level="none",
                  english_required=False, degree_level="unknown", is_internship=True)
    return JobPosting.model_validate(values | changes)


def evaluated(predictions: dict[str, JobPosting | None], version: int = 2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score predictions against two labelled postings, as evaluate.main would."""
    labels = {"001": posting(start="asap"), "002": posting()}
    details = detail_rows(labels, predictions, {"001": "en", "002": "de"})
    return details, summarize(details).assign(metric_version=version)


def test_report() -> None:
    """The report lists failures, scores per language and the paired change."""
    runs = {"a v1": evaluated({"001": posting(), "002": None}),
            "a v2": evaluated({"001": posting(start="asap"), "002": posting()})}
    report = build_report(runs, [("a v1", "a v2")])
    assert "| a v1 | 1 |" in report and "| a v2 | 0 |" in report
    assert "| start | normalized exact (proxy) | 0.00 | 1.00 |" in report
    assert "| a v1 | 0.00 | 0.00 | 0.00 | - |" in report
    assert "fr n=0" in report


def test_report_rejects_mixed_metric_versions() -> None:
    """Runs scored with different metric versions cannot be compared."""
    runs = {"a v1": evaluated({}, version=1), "a v2": evaluated({}, version=2)}
    with pytest.raises(SystemExit, match="different metric versions"):
        build_report(runs, [("a v1", "a v2")])
