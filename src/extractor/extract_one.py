"""CLI: extract the fields of a single posting and print them as JSON.

Usage:
    python -m extractor.extract_one data/postings/001.txt
"""

import argparse
from pathlib import Path

from extractor.llm import extract_posting, get_client, get_default_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract fields from one job posting.")
    parser.add_argument("path", type=Path, help="Path to a posting .txt file")
    parser.add_argument("--model", default=None, help="Model name (default: LLM_MODEL in .env)")
    parser.add_argument("--prompt", default="v1", help="Prompt version (default: v1)")
    args = parser.parse_args()

    posting_text = args.path.read_text(encoding="utf-8")
    model = args.model or get_default_model()

    print(f"Extracting {args.path.name} with {model} (prompt {args.prompt})...")
    posting = extract_posting(get_client(), posting_text, model, args.prompt)
    print(posting.model_dump_json(indent=2))


if __name__ == "__main__":
    main()