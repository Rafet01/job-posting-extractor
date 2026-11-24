"""Validate the labels of every split, report annotation progress, and flag postings
that appear in both the test and the development set."""

import csv
import re
import sys
from pathlib import Path

from extractor.labels import load_labels
from extractor.overlap import DUPLICATE_SHARE, shared_share
from extractor.splits import DEV, SPLITS, TEST, Split

ROOT = Path(__file__).resolve().parents[1]


def posting_texts(split: Split) -> dict[str, str]:
    """Posting id -> text for one split, or nothing if its folder does not exist yet."""
    folder = ROOT / split.postings_dir
    if not folder.is_dir():
        return {}
    return {path.stem: path.read_text(encoding="utf-8") for path in sorted(folder.glob("*.txt"))}


def check_split(split: Split, posting_ids: set[str]) -> bool:
    """Print the label progress of one split. Return False when its labels are unusable."""
    labels_path = ROOT / split.labels_path
    try:
        labels = load_labels(labels_path, split.id_pattern) if labels_path.exists() else {}
    except (OSError, ValueError, csv.Error) as error:
        print(f"{split.name}: label check failed: {error}", file=sys.stderr)
        return False

    bad_names = sorted(posting_id for posting_id in posting_ids if not re.fullmatch(split.id_pattern, posting_id))
    if bad_names:
        print(f"{split.name}: posting file names must match {split.id_pattern}: {', '.join(bad_names)}",
              file=sys.stderr)
        return False
    missing = sorted(posting_ids - labels.keys())
    print(f"{split.name}: postings with valid labels: {len(posting_ids) - len(missing)}/{len(posting_ids)}")
    if missing:
        print(f"{split.name}: still to label: {', '.join(missing)}")
    unknown = sorted(labels.keys() - posting_ids)
    if unknown:
        print(f"{split.name}: labels without a posting: {', '.join(unknown)}", file=sys.stderr)
        return False
    return True


def find_duplicates(dev: dict[str, str], test: dict[str, str]) -> list[str]:
    """Dev postings that share most of their text with a test posting."""
    found = []
    for dev_id, dev_text in dev.items():
        for test_id, test_text in test.items():
            share = shared_share(dev_text, test_text)
            if share >= DUPLICATE_SHARE:
                found.append(f"{dev_id} shares {share:.0%} of its text with test posting {test_id}")
    return found


def main() -> int:
    texts = {name: posting_texts(split) for name, split in SPLITS.items()}
    ok = all([check_split(split, set(texts[name])) for name, split in SPLITS.items()])
    duplicates = find_duplicates(texts[DEV.name], texts[TEST.name])
    for message in duplicates:
        print(f"Leakage: {message}. Remove it from the dev set.", file=sys.stderr)
    return 0 if ok and not duplicates else 1


if __name__ == "__main__":
    sys.exit(main())
