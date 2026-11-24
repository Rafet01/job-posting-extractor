"""Reading data/labels.csv: valid files load, malformed files fail with a clear message."""

import csv
from pathlib import Path

import pytest

from extractor.labels import load_labels

HEADER = ["id", "language", "company", "role_title", "locations", "workload_min", "workload_max",
          "duration_months", "start", "german_level", "english_required", "degree_level",
          "is_internship", "required_skills", "notes"]


def label_row(**changes: str) -> dict[str, str]:
    """One labelled posting as it is written in the CSV, with optional replacements."""
    row = dict(id="001", language="en", company="Example", role_title="Data Intern",
               locations="Basel;Zürich", workload_min="80", workload_max="100", duration_months="",
               start="", german_level="plus", english_required="true", degree_level="bachelor_ok",
               is_internship="true", required_skills="python;aws|azure", notes="")
    return row | changes


def write_labels(tmp_path: Path, rows: list[dict[str, str]], header: list[str] = HEADER) -> Path:
    """Write a labels file the way Excel saves UTF-8 CSV: with a byte order mark."""
    path = tmp_path / "labels.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_valid_file_is_loaded_by_id(tmp_path: Path) -> None:
    """Lists are split on ';', alternatives stay together and empty cells become null."""
    labels = load_labels(write_labels(tmp_path, [label_row(), label_row(id="002", locations="")]))
    assert list(labels) == ["001", "002"]
    first = labels["001"]
    assert first.locations == ["Basel", "Zürich"]
    assert first.required_skills == ["python", "aws|azure"]
    assert first.english_required is True and first.workload_min == 80
    assert first.duration_months is None and first.start is None
    assert labels["002"].locations == []


@pytest.mark.parametrize("header", [
    [column for column in HEADER if column != "notes"],
    [column.replace("locations", "location") for column in HEADER],
    HEADER + ["company"],
])
def test_wrong_header_is_rejected(tmp_path: Path, header: list[str]) -> None:
    """A missing, renamed or repeated column fails before any row is read, and lists the expected columns."""
    path = write_labels(tmp_path, [label_row()], header=header)
    with pytest.raises(ValueError, match="invalid CSV header. Expected columns"):
        load_labels(path)


def test_duplicate_id_is_rejected(tmp_path: Path) -> None:
    """Two rows for one posting would make the evaluation count it twice."""
    path = write_labels(tmp_path, [label_row(), label_row(company="Other")])
    with pytest.raises(ValueError, match="line 3: duplicate ID 001"):
        load_labels(path)


@pytest.mark.parametrize("posting_id", ["1", "01", "0001", "A01"])
def test_id_without_three_digits_is_rejected(tmp_path: Path, posting_id: str) -> None:
    """IDs must match the posting filenames, e.g. when a spreadsheet dropped the leading zeros."""
    path = write_labels(tmp_path, [label_row(id=posting_id)])
    with pytest.raises(ValueError, match=f"expected a three-digit ID, got '{posting_id}'"):
        load_labels(path)


@pytest.mark.parametrize("field, value", [
    ("german_level", "fluent"), ("english_required", "maybe"), ("workload_min", "80%"),
    ("degree_level", ""),
])
def test_invalid_value_names_the_line_id_and_field(tmp_path: Path, field: str, value: str) -> None:
    """Labels pass the same validation as model answers. The message points to the cell."""
    path = write_labels(tmp_path, [label_row(id="001"), label_row(id="002", **{field: value})])
    # (?s) lets .* cross the line break before Pydantic's field name.
    with pytest.raises(ValueError, match=rf"(?s)line 3, ID 002: .*{field}"):
        load_labels(path)


def test_row_with_wrong_number_of_columns_is_rejected(tmp_path: Path) -> None:
    """A missing or extra comma shifts every later cell, so the row is refused."""
    path = write_labels(tmp_path, [label_row()])
    with path.open("a", encoding="utf-8", newline="") as file:
        file.write("002,en,Example,Data Intern\n")
    with pytest.raises(ValueError, match="line 3: wrong number of columns"):
        load_labels(path)
