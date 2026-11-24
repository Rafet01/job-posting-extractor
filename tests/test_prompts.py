"""Prompt versions stay reproducible and contain no text from the test postings."""

import hashlib
import json
import re
from pathlib import Path

import pytest

from extractor.prompts import PROMPTS, build_messages, schema_for, without_descriptions

POSTINGS_DIR = Path(__file__).resolve().parents[1] / "data" / "postings"

# SHA-256 of each system prompt as used for the cached runs. A cached run is only
# valid for the exact prompt that produced it, so changing a prompt means a new version.
PROMPT_HASHES = {
    "v1": "1053ec14213c35772f3a30c93962bc6a60526763dbb0dbffe7430533d72450d8",
    "v2": "08904b5efc69372b2ff0d1e746b67d9c311661923635b6d05d3d07e24929fd06",
}


@pytest.mark.parametrize("version", PROMPT_HASHES)
def test_prompt_is_frozen(version: str) -> None:
    """The system prompt still matches the text the cached results were produced with."""
    system_prompt = build_messages("posting", version)[0]["content"]
    assert hashlib.sha256(system_prompt.encode()).hexdigest() == PROMPT_HASHES[version]


def test_messages() -> None:
    """Every version sends one system prompt and the posting text, fully formatted."""
    for version in PROMPTS:
        messages = build_messages("Data Intern\nExample AG\nBern", version)
        assert [message["role"] for message in messages] == ["system", "user"]
        assert messages[1]["content"] == "Data Intern\nExample AG\nBern"
        assert "{schema}" not in messages[0]["content"]
    with pytest.raises(ValueError, match="Unknown prompt version"):
        build_messages("posting", "v99")


def test_v2_schema_keeps_structure() -> None:
    """v2 drops the v1 field descriptions but keeps every type, enum and bound."""
    v1, v2 = json.loads(schema_for("v1")), json.loads(schema_for("v2"))
    assert "description" in v1["properties"]["degree_level"]
    assert '"description"' not in schema_for("v2")
    assert v2 == without_descriptions(v1)
    assert v2["properties"]["degree_level"]["enum"] == v1["properties"]["degree_level"]["enum"]


def test_without_descriptions() -> None:
    """Descriptions disappear at every depth, including inside lists."""
    schema = {"description": "x", "anyOf": [{"type": "null", "description": "y"}], "title": "T"}
    assert without_descriptions(schema) == {"anyOf": [{"type": "null"}], "title": "T"}


def word_ngrams(text: str, n: int) -> set[tuple[str, ...]]:
    """All sequences of n consecutive lowercase words."""
    words = re.findall(r"\w+", text.lower())
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


@pytest.mark.parametrize("version", [version for version in PROMPTS if version != "v1"])
def test_no_posting_text_in_prompt(version: str) -> None:
    """Instructions written for a version share no five-word sequence with a test posting.

    Shorter overlaps are allowed: they are generic phrases such as 'as soon as possible'.
    """
    prompt = word_ngrams(build_messages("", version)[0]["content"], 5)
    postings = sorted(POSTINGS_DIR.glob("*.txt"))
    assert postings, "expected the test postings in data/postings"
    for path in postings:
        shared = prompt & word_ngrams(path.read_text(encoding="utf-8"), 5)
        assert not shared, f"{path.name} shares {sorted(' '.join(gram) for gram in shared)}"
