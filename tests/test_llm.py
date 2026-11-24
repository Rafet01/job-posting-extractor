"""The LLM call, with a mocked client: validation, retries and errors."""

import json
import socket
from types import SimpleNamespace
from unittest.mock import MagicMock

import openai
import pytest

from extractor.llm import ExtractionError, extract_posting, get_client
from extractor.prompts import build_messages
from tests.factories import posting, posting_fields

POSTING_TEXT = "Data Intern\nExample\nZurich\n\nYou will analyse data."
VALID_ANSWER = json.dumps(posting_fields())
INVALID_ANSWER = json.dumps(posting_fields(german_level="fluent"))


def completion(content: str | None) -> SimpleNamespace:
    """The part of an OpenAI chat completion response that extract_posting reads."""
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def mock_client(*answers: str | None | Exception) -> MagicMock:
    """A client whose successive calls return these answers, or raise them if they are errors."""
    client = MagicMock()
    client.chat.completions.create.side_effect = [
        answer if isinstance(answer, Exception) else completion(answer) for answer in answers
    ]
    return client


def sent_messages(client: MagicMock, call: int) -> list[dict[str, str]]:
    """The messages the client received in its n-th call, counting from zero."""
    return client.chat.completions.create.call_args_list[call].kwargs["messages"]


def test_valid_answer_is_returned_as_job_posting() -> None:
    """One valid answer gives a JobPosting after a single, deterministic JSON request."""
    client = mock_client(VALID_ANSWER)
    assert extract_posting(client, POSTING_TEXT, "demo-model") == posting()
    client.chat.completions.create.assert_called_once_with(
        model="demo-model", messages=build_messages(POSTING_TEXT, "v1"),
        response_format={"type": "json_object"}, temperature=0,
    )


def test_prompt_version_selects_the_system_prompt() -> None:
    """The requested prompt version is the one sent to the model."""
    client = mock_client(VALID_ANSWER)
    extract_posting(client, POSTING_TEXT, "demo-model", prompt_version="v2")
    assert sent_messages(client, 0) == build_messages(POSTING_TEXT, "v2")


def test_invalid_answer_is_retried_with_the_validation_error() -> None:
    """The retry repeats the conversation, adds the invalid answer and explains what was wrong."""
    client = mock_client(INVALID_ANSWER, VALID_ANSWER)
    assert extract_posting(client, POSTING_TEXT, "demo-model") == posting()

    first, retry = sent_messages(client, 0), sent_messages(client, 1)
    assert len(first) == 2
    assert retry[:2] == first
    assert retry[2] == {"role": "assistant", "content": INVALID_ANSWER}
    assert retry[3]["role"] == "user"
    assert "german_level" in retry[3]["content"]
    assert "Return the corrected JSON only" in retry[3]["content"]


@pytest.mark.parametrize("answer", ["Sure! Here is the JSON you asked for.", "", None])
def test_answer_that_is_not_json_is_retried(answer: str | None) -> None:
    """Prose, an empty string or no content at all count as invalid answers."""
    client = mock_client(answer, VALID_ANSWER)
    assert extract_posting(client, POSTING_TEXT, "demo-model") == posting()
    assert client.chat.completions.create.call_count == 2


@pytest.mark.parametrize("max_attempts", [1, 3])
def test_gives_up_with_a_clear_error_after_the_last_attempt(max_attempts: int) -> None:
    """After max_attempts invalid answers, ExtractionError says how many attempts were made."""
    client = mock_client(*[INVALID_ANSWER] * max_attempts)
    with pytest.raises(ExtractionError, match=f"No valid answer after {max_attempts} attempts"):
        extract_posting(client, POSTING_TEXT, "demo-model", max_attempts=max_attempts)
    assert client.chat.completions.create.call_count == max_attempts


def test_connection_error_is_not_swallowed() -> None:
    """An unreachable server is raised immediately, not retried as if the answer were invalid."""
    client = mock_client(openai.APIConnectionError(request=None))
    with pytest.raises(openai.APIConnectionError):
        extract_posting(client, POSTING_TEXT, "demo-model")
    assert client.chat.completions.create.call_count == 1


def test_client_uses_the_settings_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """The base URL and key come from .env or the environment. Creating a client sends nothing."""
    monkeypatch.setenv("LLM_BASE_URL", "http://llm.example/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    client = get_client()
    assert str(client.base_url).startswith("http://llm.example/v1")
    assert client.api_key == "test-key"


def test_test_suite_blocks_real_network_access() -> None:
    """The guard in conftest.py turns any forgotten real LLM call into a test failure."""
    with pytest.raises(RuntimeError, match="must not open network connections"):
        socket.create_connection(("127.0.0.1", 11434), timeout=1)
