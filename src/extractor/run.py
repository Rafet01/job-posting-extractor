"""CLI: extract all postings with one model and prompt version, using a cache.

Usage:
    python -m extractor.run --model llama3.1 --prompt v1
"""

import argparse
import time
from pathlib import Path

from extractor.llm import ExtractionError, extract_posting, get_client, get_default_model
from extractor.schema import JobPosting

POSTINGS_DIR = Path("data/postings")
CACHE_DIR = Path("outputs/cache")


def cache_path(model: str, prompt_version: str, posting_id: str) -> Path:
    """Where the result for one posting/model/prompt combination is stored."""
    # ':' is not allowed in Windows folder names, e.g. 'qwen2.5:7b'.
    safe_model = model.replace(":", "_").replace("/", "_")
    return CACHE_DIR / safe_model / prompt_version / f"{posting_id}.json"


def load_cached(path: Path) -> JobPosting | None:
    """Return the cached result, or None if there is none."""
    if not path.exists():
        return None
    return JobPosting.model_validate_json(path.read_text(encoding="utf-8"))


def save_cached(path: Path, posting: JobPosting) -> None:
    """Store a validated result as pretty-printed JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(posting.model_dump_json(indent=2), encoding="utf-8")


def run(model: str, prompt_version: str, force: bool = False) -> None:
    """Extract every posting in POSTINGS_DIR, skipping cached ones unless force is set."""
    client = get_client()
    files = sorted(POSTINGS_DIR.glob("*.txt"))
    counts = {"cached": 0, "extracted": 0, "failed": 0, "skipped": 0}

    print(f"{len(files)} postings, model={model}, prompt={prompt_version}")

    for file in files:
        posting_id = file.stem  # '001.txt' -> '001'
        path = cache_path(model, prompt_version, posting_id)

        if not force and path.exists():
            counts["cached"] += 1
            continue

        text = file.read_text(encoding="utf-8").strip()
        if len(text) < 50:
            print(f"[{posting_id}] skipped: text is empty or too short")
            counts["skipped"] += 1
            continue

        start = time.perf_counter()
        try:
            posting = extract_posting(client, text, model, prompt_version)
        except ExtractionError as error:
            print(f"[{posting_id}] FAILED: {error}")
            counts["failed"] += 1
            continue

        save_cached(path, posting)
        counts["extracted"] += 1
        print(f"[{posting_id}] ok in {time.perf_counter() - start:.1f}s")

    print(f"Done: {counts}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract fields from all job postings.")
    parser.add_argument("--model", default=None, help="Model name (default: LLM_MODEL in .env)")
    parser.add_argument("--prompt", default="v1", help="Prompt version (default: v1)")
    parser.add_argument("--force", action="store_true", help="Ignore the cache and extract again")
    args = parser.parse_args()

    run(args.model or get_default_model(), args.prompt, args.force)


if __name__ == "__main__":
    main()