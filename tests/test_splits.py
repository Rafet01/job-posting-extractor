"""The data splits keep their files apart, and the test split keeps the published paths."""

import csv
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import extractor.run as run_module
from extractor.evaluate import output_path
from extractor.labels import load_labels
from extractor.run import cache_path
from extractor.splits import DEV, TEST
from tests.factories import posting


def test_test_split_uses_the_published_paths() -> None:
    """Postings, labels, cache and result files stay where version 1 put them."""
    assert TEST.postings_dir == Path("data/postings")
    assert TEST.labels_path == Path("data/labels.csv")
    assert cache_path("qwen2.5:7b", "v1", "001") == Path("outputs/cache/qwen2.5_7b/v1/001.json")
    assert output_path("summary", "llama3.1", "v2") == Path("outputs/summary_llama3.1_v2.csv")


def test_dev_split_never_shares_a_folder_or_an_id_with_the_test_split() -> None:
    """Dev postings, labels, cache and results live apart, and dev ids cannot look like test ids."""
    assert DEV.postings_dir == Path("data/dev/postings")
    assert DEV.labels_path == Path("data/dev/labels.csv")
    assert cache_path("llama3.1", "v1", "d001", DEV) == Path("outputs/dev/cache/llama3.1/v1/d001.json")
    assert output_path("summary", "llama3.1", "v1", DEV) == Path("outputs/dev/summary_llama3.1_v1.csv")
    assert not re.fullmatch(DEV.id_pattern, "001")
    assert not re.fullmatch(TEST.id_pattern, "d001")


def test_dev_labels_reject_a_test_id(tmp_path: Path) -> None:
    """A test posting id in the dev labels is an error, not a silent mix of the two sets."""
    row = {"id": "001", "language": "en", "notes": ""} | posting().model_dump(mode="json")
    row["locations"] = row["required_skills"] = ""
    path = tmp_path / "labels.csv"
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(row))
        writer.writeheader()
        writer.writerow({key: "" if value is None else str(value).lower() if isinstance(value, bool) else value
                         for key, value in row.items()})
    with pytest.raises(ValueError, match=r"expected an ID matching d\[0-9\]\{3\}, got '001'"):
        load_labels(path, DEV.id_pattern)


def test_run_on_the_dev_split_reads_and_writes_only_dev_folders(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Extracting the dev split caches under outputs/dev/cache and leaves the test cache alone."""
    monkeypatch.chdir(tmp_path)
    DEV.postings_dir.mkdir(parents=True)
    (DEV.postings_dir / "d001.txt").write_text("Data Intern\nExample AG\nZurich\n\n" + "Text. " * 20,
                                               encoding="utf-8")
    monkeypatch.setattr(run_module, "get_client", MagicMock())
    monkeypatch.setattr(run_module, "extract_posting", lambda *args: posting())

    run_module.run("demo:7b", "v1", split=DEV)

    assert cache_path("demo:7b", "v1", "d001", DEV).exists()
    assert not TEST.cache_dir.exists()
