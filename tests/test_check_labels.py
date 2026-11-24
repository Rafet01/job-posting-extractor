"""scripts/check_labels.py: progress per split, and dev postings copied from the test set."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from extractor.overlap import shared_share
from extractor.splits import DEV, TEST

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_labels.py"
HEADER = ("id,language,company,role_title,locations,workload_min,workload_max,duration_months,start,"
          "german_level,english_required,degree_level,is_internship,required_skills,notes\n")
AD = ("Data Intern\nExample AG\nZurich\n\nYou will build dashboards for our sales team and "
      "automate weekly reports. You bring Python and SQL, curiosity and a sense of humour.")


@pytest.fixture
def check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load the script with its project root pointed at an empty temporary folder."""
    spec = importlib.util.spec_from_file_location("check_labels", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    return module


def add(root: Path, split_dir: Path, posting_id: str, text: str, label: str | None = None) -> None:
    """Write one posting, and optionally its label row, into a split under root."""
    (root / split_dir / "postings").mkdir(parents=True, exist_ok=True)
    (root / split_dir / "postings" / f"{posting_id}.txt").write_text(text, encoding="utf-8")
    labels = root / split_dir / "labels.csv"
    if not labels.exists():
        labels.write_text(HEADER, encoding="utf-8")
    if label:
        with labels.open("a", encoding="utf-8") as file:
            file.write(f"{posting_id},{label}\n")


def test_shared_share_separates_a_copy_from_a_different_ad() -> None:
    """A copied ad shares all its five-word sequences, a different ad almost none."""
    assert shared_share(AD, AD) == 1.0
    assert shared_share(AD, "Software Engineer\nOther SA\nGeneva\n\nYou maintain our payment backend in Java.") == 0.0
    assert shared_share("too short", AD) == 0.0


def test_progress_is_reported_per_split(check: ModuleType, tmp_path: Path,
                                        capsys: pytest.CaptureFixture[str]) -> None:
    """Each split reports its own count, and an empty dev set is not an error."""
    add(tmp_path, TEST.data_dir, "001", AD, "en,Example,Data Intern,Zurich,,,,,none,false,unknown,true,python;sql,")
    add(tmp_path, TEST.data_dir, "002", AD + " Another ad.")
    assert check.main() == 0
    output = capsys.readouterr().out
    assert "test: postings with valid labels: 1/2" in output
    assert "test: still to label: 002" in output
    assert "dev: postings with valid labels: 0/0" in output


def test_dev_posting_copied_from_the_test_set_fails_the_check(
        check: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The same ad in both sets is leakage: the check names both ids and fails."""
    add(tmp_path, TEST.data_dir, "001", AD)
    add(tmp_path, DEV.data_dir, "d001", AD)
    assert check.main() == 1
    assert "d001 shares 100% of its text with test posting 001" in capsys.readouterr().err


def test_dev_file_with_a_test_style_name_fails_the_check(
        check: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A dev posting saved as 027.txt instead of d001.txt is reported instead of silently ignored."""
    add(tmp_path, DEV.data_dir, "027", AD)
    assert check.main() == 1
    assert "dev: posting file names must match" in capsys.readouterr().err
