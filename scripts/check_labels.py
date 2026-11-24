"""Validate the current labels and report annotation progress."""

import csv
import sys
from pathlib import Path

from extractor.labels import load_labels


def main() -> int:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    try:
        labels = load_labels(data_dir / "labels.csv")
        posting_ids = {
            path.stem for path in (data_dir / "postings").iterdir()
            if path.suffix == ".txt" and path.is_file()
        }
    except (OSError, ValueError, csv.Error) as error:
        print(f"Label check failed: {error}", file=sys.stderr)
        return 1

    missing = sorted(posting_ids - labels.keys())
    print(f"Postings with valid labels: {len(posting_ids) - len(missing)}/{len(posting_ids)}")
    if missing:
        print(f"Still to label: {', '.join(missing)}")

    unknown = sorted(labels.keys() - posting_ids)
    if unknown:
        print(f"Labels without a posting: {', '.join(unknown)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
