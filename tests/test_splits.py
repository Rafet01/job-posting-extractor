"""The data splits keep their files apart, and the test split keeps the published paths."""

from pathlib import Path

from extractor.evaluate import output_path
from extractor.run import cache_path
from extractor.splits import TEST


def test_test_split_uses_the_published_paths() -> None:
    """Postings, labels, cache and result files stay where version 1 put them."""
    assert TEST.postings_dir == Path("data/postings")
    assert TEST.labels_path == Path("data/labels.csv")
    assert cache_path("qwen2.5:7b", "v1", "001") == Path("outputs/cache/qwen2.5_7b/v1/001.json")
    assert output_path("summary", "llama3.1", "v2") == Path("outputs/summary_llama3.1_v2.csv")
