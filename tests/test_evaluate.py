"""Scoring cached runs against the labels, and exporting the results."""

import csv
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from extractor.evaluate import detail_rows, main, summarize
from extractor.run import cache_path
from extractor.schema import JobPosting
from tests.factories import posting


def label(**changes: object) -> JobPosting:
    """A labelled posting with two locations and a skill requirement with alternatives."""
    return posting(**({"company": "Example AG", "role_title": "Engineer", "locations": ["Zurich", "Bern"],
                       "required_skills": ["python", "aws|azure"], "german_level": "required"} | changes))


def overall(details: pd.DataFrame) -> pd.Series:
    """Overall score per field."""
    scores = summarize(details)
    return scores[scores.language == "overall"].set_index("field").score


def test_failed_extraction_scores_zero_on_every_field() -> None:
    """A posting without a valid prediction stays in every denominator, even where the label is null."""
    details = detail_rows({"001": label()}, {}, {"001": "en"})
    assert len(details) == len(JobPosting.model_fields)
    assert details.score.eq(0).all() and details.missing_prediction.all()


def test_scores_are_averaged_over_all_labelled_postings() -> None:
    """Posting 001 is predicted with spelling variants and partial lists. Posting 002 failed."""
    labels = {"001": label(), "002": label(german_level="plus")}
    predictions = {"001": label(company="Example", role_title="ENGINEER",
                                locations=["Zürich"], required_skills=["Azure"])}
    scores = overall(detail_rows(labels, predictions, {"001": "en", "002": "en"}))
    # The legal suffix and case are normalised and start is null on both sides, so 001 scores 1.
    for field in ("company", "role_title", "start"):
        assert scores[field] == 0.5
    # One of two locations: F1 2/3. Azure satisfies one of two requirements: F1 2/3.
    assert scores["locations"] == pytest.approx(1 / 3)
    assert scores["required_skills"] == pytest.approx(1 / 3)
    assert scores["german_level"] == 0.5


def test_each_language_has_its_own_denominator() -> None:
    """Language scores count only that language's postings, and an empty group has no score."""
    details = detail_rows({"001": label(), "002": label()}, {"001": label()}, {"001": "de", "002": "fr"})
    scores = summarize(details).set_index(["language", "field"])
    assert scores.at[("de", "company"), "score"] == 1.0
    assert scores.at[("fr", "company"), "n"] == 1
    assert scores.at[("fr", "company"), "missing_predictions"] == 1
    assert pd.isna(scores.at[("en", "company"), "score"])


def test_class_fields_use_macro_f1_so_majority_guessing_scores_low() -> None:
    """Always predicting the majority class: 2 of 3 correct, but macro F1 is only 0.4."""
    labels = {"001": label(is_internship=False), "002": label(is_internship=False), "003": label()}
    predictions = dict.fromkeys(labels, label(is_internship=False))
    scores = overall(detail_rows(labels, predictions, dict.fromkeys(labels, "en")))
    assert scores["is_internship"] == pytest.approx(0.4)


def write_labels(*ids: str) -> None:
    """Write data/labels.csv in the working folder with the default label for each id."""
    Path("data").mkdir()
    rows = []
    for posting_id in ids:
        row = label().model_dump() | {"id": posting_id, "language": "en", "notes": ""}
        row["locations"], row["required_skills"] = ";".join(row["locations"]), ";".join(row["required_skills"])
        rows.append(row)
    with Path("data/labels.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_cache(posting_id: str, content: str) -> None:
    """Write one cache file for the demo run."""
    cache = cache_path("demo:7b", "v1", posting_id)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(content, encoding="utf-8")


def test_command_scores_invalid_cache_as_missing_and_writes_csvs(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI reads labels and cache from the working folder and exports null predictions as JSON."""
    monkeypatch.chdir(tmp_path)
    write_labels("001", "002")
    write_cache("001", "{}")
    write_cache("002", label(required_skills=["python", "aws"]).model_dump_json())
    monkeypatch.setattr(sys, "argv", ["evaluate", "--model", "demo:7b", "--prompt", "v1"])

    main()

    details = pd.read_csv("outputs/details_demo_7b_v1.csv", dtype={"id": str}, keep_default_na=False)
    assert details.id.unique().tolist() == ["001", "002"]
    invalid = details[details.id == "001"]
    assert invalid.score.eq(0).all()
    assert json.loads(invalid.pred.iloc[0]) is None
    assert details[details.id == "002"].score.eq(1).all()
    assert Path("outputs/summary_demo_7b_v1.csv").exists()


def test_command_without_any_cached_prediction_writes_nothing(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """On a fresh clone there is no cache: stop with a hint instead of publishing all zeros."""
    monkeypatch.chdir(tmp_path)
    write_labels("001", "002")
    Path("outputs").mkdir()
    published = Path("outputs/summary_demo_7b_v1.csv")
    published.write_text("published results", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["evaluate", "--model", "demo:7b", "--prompt", "v1"])

    with pytest.raises(SystemExit, match="python -m extractor.run --model demo:7b"):
        main()

    assert published.read_text(encoding="utf-8") == "published results"
    assert not Path("outputs/details_demo_7b_v1.csv").exists()
