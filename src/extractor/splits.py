"""Where each data split keeps its postings, labels, cache and results.

The test split is the published one: its paths are the ones the project has always used.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Split:
    """One set of postings with its labels, and the folders its runs write to."""

    name: str
    data_dir: Path
    output_dir: Path
    id_pattern: str  # regular expression every posting id in this split must match

    @property
    def postings_dir(self) -> Path:
        """The posting texts, one .txt file per id."""
        return self.data_dir / "postings"

    @property
    def labels_path(self) -> Path:
        """The hand labels for this split."""
        return self.data_dir / "labels.csv"

    @property
    def cache_dir(self) -> Path:
        """Validated LLM answers, per model and prompt version."""
        return self.output_dir / "cache"


TEST = Split("test", data_dir=Path("data"), output_dir=Path("outputs"), id_pattern=r"[0-9]{3}")
SPLITS = {split.name: split for split in (TEST,)}
