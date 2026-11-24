"""Offline integration tests for scoring and exporting cached runs."""

import csv
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from extractor.evaluate import detail_rows, main, summarize
from extractor.run import cache_path
from extractor.schema import JobPosting


def posting(**changes: object) -> JobPosting:
    """Create a small valid posting, optionally replacing individual fields."""
    values = dict(company="Example AG", role_title="Engineer", locations=["Zurich", "Bern"],
                  required_skills=["python", "aws|azure"], german_level="required",
                  english_required=True, degree_level="unknown", is_internship=False)
    return JobPosting.model_validate(values | changes)


def test_field_scores_and_missing_prediction() -> None:
    """Use every label in each denominator, including nulls in a failed posting."""
    labels = {"001": posting(), "002": posting(german_level="plus")}
    predictions = {"001": posting(company="Example", role_title="ENGINEER",
                                  locations=["Zürich"], required_skills=["Azure"])}
    details = detail_rows(labels, predictions, {"001": "de", "002": "fr"})
    assert len(details) == 2 * len(JobPosting.model_fields)
    assert details[details.id == "002"].score.eq(0).all()
    scores = summarize(details).set_index(["language", "field"])
    assert scores.at[("overall", "german_level"), "score"] == 0.5
    assert scores.at[("overall", "required_skills"), "score"] == pytest.approx(1/3)
    assert scores.at[("overall", "locations"), "score"] == pytest.approx(1/3)
    for field in ("company", "role_title", "start"):
        assert scores.at[("overall", field), "score"] == 0.5
    assert scores.at[("fr", "degree_level"), "n"] == 1
    assert scores.at[("fr", "degree_level"), "missing_predictions"] == 1
    assert pd.isna(scores.at[("en", "company"), "score"])


def test_majority_class() -> None:
    """Two correct majority guesses out of three give macro F1 of 0.4."""
    labels = {"001": posting(), "002": posting(), "003": posting(is_internship=True)}
    details = detail_rows(labels, dict.fromkeys(labels, posting()), dict.fromkeys(labels, "en"))
    scores = summarize(details).set_index(["language", "field"])
    assert scores.at[("overall", "is_internship"), "score"] == pytest.approx(0.4)


def test_command_exports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the CLI with an invalid cached JSON and inspect the exported row."""
    monkeypatch.chdir(tmp_path)
    Path("data").mkdir()
    row = posting().model_dump()
    for field in ("locations", "required_skills"):
        row[field] = ";".join(row[field])
    row.update(id="001", language="en", notes="")
    with Path("data/labels.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    cache = cache_path("demo:7b", "v1", "001")
    cache.parent.mkdir(parents=True)
    cache.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["evaluate", "--model", "demo:7b", "--prompt", "v1"])
    main()
    details = pd.read_csv("outputs/details_demo_7b_v1.csv", dtype={"id": str}, keep_default_na=False)
    assert details.id.unique().tolist() == ["001"]
    assert details.score.eq(0).all()
    assert json.loads(details.pred.iloc[0]) is None
    assert Path("outputs/summary_demo_7b_v1.csv").exists()
