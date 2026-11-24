"""Read hand-labelled postings for evaluation."""

import csv
import re
from pathlib import Path

from pydantic import ValidationError

from extractor.schema import JobPosting


def load_labels(path: str | Path = Path("data/labels.csv"),
                id_pattern: str = r"[0-9]{3}") -> dict[str, JobPosting]:
    """Return validated postings keyed by their IDs, which must match id_pattern.

    The default pattern is the test split's: three digits, as in the posting filenames.
    Language and notes are annotation metadata, outside the extraction schema.
    """
    labels: dict[str, JobPosting] = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, strict=True)
        columns = reader.fieldnames or []
        expected = {"id", "language", "notes", *JobPosting.model_fields}
        if set(columns) != expected or len(columns) != len(expected):
            raise ValueError(f"{path}: invalid CSV header. Expected columns: {sorted(expected)}")

        for row in reader:
            context = f"{path}, line {reader.line_num}"
            if None in row or None in row.values():
                raise ValueError(f"{context}: wrong number of columns")

            posting_id = row["id"].strip()
            if not re.fullmatch(id_pattern, posting_id):
                expected = "a three-digit ID" if id_pattern == r"[0-9]{3}" else f"an ID matching {id_pattern}"
                raise ValueError(f"{context}: expected {expected}, got {posting_id!r}")
            if posting_id in labels:
                raise ValueError(f"{context}: duplicate ID {posting_id}")

            fields = {name: row[name].strip() or None for name in JobPosting.model_fields}
            for name in ("locations", "required_skills"):
                fields[name] = [item.strip() for item in row[name].split(";") if item.strip()]

            try:
                labels[posting_id] = JobPosting.model_validate(fields)
            except ValidationError as error:
                raise ValueError(f"{context}, ID {posting_id}: {error}") from error

    return labels
