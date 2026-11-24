"""The batch run: caching, failures and skipped postings, in temporary folders."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import openai
import pytest

import extractor.run as run_module
from extractor.llm import ExtractionError
from extractor.run import cache_path, load_cached, run
from extractor.schema import JobPosting
from extractor.splits import TEST
from tests.factories import posting, posting_fields

MODEL, PROMPT = "demo:7b", "v1"


class FakeExtraction:
    """Replaces extract_posting: records each posting sent and fails postings marked FAIL."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    def __call__(self, client: object, text: str, model: str, prompt_version: str) -> JobPosting:
        posting_id = text.split()[0]
        self.sent.append(posting_id)
        if "FAIL" in text:
            raise ExtractionError("No valid answer after 3 attempts")
        return posting(role_title=f"Title {posting_id}")


@pytest.fixture
def postings_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the run at empty temporary posting and cache folders, never at data/ or outputs/."""
    monkeypatch.chdir(tmp_path)  # every split path is relative, so data/ and outputs/ are temporary
    postings = TEST.postings_dir
    postings.mkdir(parents=True)
    monkeypatch.setattr(run_module, "get_client", MagicMock())
    return postings


@pytest.fixture
def extraction(postings_dir: Path, monkeypatch: pytest.MonkeyPatch) -> FakeExtraction:
    """Replace the LLM call by a fake that needs no client."""
    fake = FakeExtraction()
    monkeypatch.setattr(run_module, "extract_posting", fake)
    return fake


def add_posting(postings_dir: Path, posting_id: str, extra: str = "") -> None:
    """Write a posting long enough to be extracted. Its text starts with its ID."""
    text = f"{posting_id} {extra}\nExample AG\nZurich\n\nWe are looking for a data intern to join our team."
    (postings_dir / f"{posting_id}.txt").write_text(text, encoding="utf-8")


def cached_title(posting_id: str) -> str | None:
    """The role title stored in the cache for a posting, or None if nothing valid is cached."""
    result = load_cached(cache_path(MODEL, PROMPT, posting_id))
    return result.role_title if result else None


def test_new_postings_are_extracted_and_cached(postings_dir: Path, extraction: FakeExtraction) -> None:
    """Every posting without a cached result is sent once and its result is stored."""
    add_posting(postings_dir, "001")
    add_posting(postings_dir, "002")
    run(MODEL, PROMPT)
    assert extraction.sent == ["001", "002"]
    assert cached_title("001") == "Title 001" and cached_title("002") == "Title 002"


def test_cached_postings_are_skipped(postings_dir: Path, extraction: FakeExtraction,
                                     capsys: pytest.CaptureFixture[str]) -> None:
    """A second run sends nothing to the model and reports the postings as cached."""
    add_posting(postings_dir, "001")
    run(MODEL, PROMPT)
    run(MODEL, PROMPT)
    assert extraction.sent == ["001"]
    assert "'cached': 1, 'extracted': 0" in capsys.readouterr().out


def test_force_extracts_cached_postings_again(postings_dir: Path, extraction: FakeExtraction) -> None:
    """--force ignores the cache."""
    add_posting(postings_dir, "001")
    run(MODEL, PROMPT)
    run(MODEL, PROMPT, force=True)
    assert extraction.sent == ["001", "001"]


def test_cache_is_kept_per_model_and_prompt(postings_dir: Path, extraction: FakeExtraction) -> None:
    """A result for one prompt version is never reused for another."""
    add_posting(postings_dir, "001")
    run(MODEL, "v1")
    run(MODEL, "v2")
    assert extraction.sent == ["001", "001"]
    # ':' is not allowed in Windows folder names.
    assert cache_path("qwen2.5:7b", "v2", "001") == TEST.cache_dir / "qwen2.5_7b" / "v2" / "001.json"


def test_failed_posting_is_reported_and_not_cached(postings_dir: Path, extraction: FakeExtraction,
                                                   capsys: pytest.CaptureFixture[str]) -> None:
    """A posting without a valid answer is reported, left uncached and does not stop the run."""
    add_posting(postings_dir, "001", "FAIL")
    add_posting(postings_dir, "002")
    run(MODEL, PROMPT)
    output = capsys.readouterr().out
    assert "[001] FAILED: No valid answer after 3 attempts" in output
    assert "'extracted': 1, 'failed': 1" in output
    assert cached_title("001") is None
    assert cached_title("002") == "Title 002"


def test_failed_posting_is_tried_again_in_the_next_run(postings_dir: Path, extraction: FakeExtraction) -> None:
    """Because a failure is not cached, rerunning the command retries only that posting."""
    add_posting(postings_dir, "001", "FAIL")
    add_posting(postings_dir, "002")
    run(MODEL, PROMPT)
    run(MODEL, PROMPT)
    assert extraction.sent == ["001", "002", "001"]


@pytest.mark.parametrize("text", ["", "   \n\n  ", "Data Intern\nExample AG"])
def test_empty_or_very_short_posting_is_skipped_without_calling_the_model(
        postings_dir: Path, extraction: FakeExtraction, capsys: pytest.CaptureFixture[str], text: str) -> None:
    """Texts under 50 characters are reported as skipped, the rest of the run continues."""
    (postings_dir / "001.txt").write_text(text, encoding="utf-8")
    add_posting(postings_dir, "002")
    run(MODEL, PROMPT)
    output = capsys.readouterr().out
    assert extraction.sent == ["002"]
    assert "[001] skipped" in output and "'skipped': 1" in output
    assert not cache_path(MODEL, PROMPT, "001").exists()


@pytest.mark.parametrize("stale", [
    json.dumps(posting_fields(location="Basel")),  # an older schema with a single location
    json.dumps(posting_fields(german_level="fluent")),
    '{"company": "Exa',  # a write that was interrupted
])
def test_outdated_or_broken_cache_file_is_extracted_again(
        postings_dir: Path, extraction: FakeExtraction, stale: str) -> None:
    """A cached file that no longer matches the schema counts as missing and is replaced."""
    add_posting(postings_dir, "001")
    path = cache_path(MODEL, PROMPT, "001")
    path.parent.mkdir(parents=True)
    path.write_text(stale, encoding="utf-8")
    run(MODEL, PROMPT)
    assert extraction.sent == ["001"]
    assert cached_title("001") == "Title 001"


def test_connection_error_stops_the_run(postings_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If the server is unreachable, the run stops instead of marking every posting as failed."""
    add_posting(postings_dir, "001")
    add_posting(postings_dir, "002")
    unreachable = MagicMock(side_effect=openai.APIConnectionError(request=None))
    monkeypatch.setattr(run_module, "extract_posting", unreachable)
    with pytest.raises(openai.APIConnectionError):
        run(MODEL, PROMPT)
    assert unreachable.call_count == 1
    assert not TEST.cache_dir.exists()


def test_run_with_mocked_client_caches_the_validated_answer(postings_dir: Path,
                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    """End to end without Ollama: run, LLM call and cache work together on one posting."""
    add_posting(postings_dir, "001")
    answer = json.dumps(posting_fields(required_skills=["Python", "SQL"]))
    client = MagicMock()
    client.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content=answer))]
    monkeypatch.setattr(run_module, "get_client", lambda: client)
    run(MODEL, PROMPT)
    assert load_cached(cache_path(MODEL, PROMPT, "001")).required_skills == ["python", "sql"]
