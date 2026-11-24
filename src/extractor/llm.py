"""LLM client and the extraction call, with retries on invalid answers."""

import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from extractor.prompts import build_messages, response_format_for
from extractor.schema import JobPosting

load_dotenv()


# A valid JobPosting answer is a few hundred tokens. The cap stops a model that keeps
# generating, for example endless whitespace under schema-constrained decoding.
MAX_TOKENS = 1024


class ExtractionError(Exception):
    """Raised when the LLM gives no valid answer after all attempts."""


def get_client() -> OpenAI:
    """Create an OpenAI-compatible client from the settings in .env."""
    return OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
    )


def get_default_model() -> str:
    """Return the model name configured in .env."""
    return os.environ["LLM_MODEL"]


def extract_posting(
    client: OpenAI,
    posting_text: str,
    model: str,
    prompt_version: str = "v1",
    max_attempts: int = 3,
) -> JobPosting:
    """Send one posting to the LLM and validate the answer with Pydantic.

    If the answer is invalid, the validation error is sent back to the model
    so it can correct itself, up to max_attempts times in total.
    """
    messages = build_messages(posting_text, prompt_version)

    for attempt in range(1, max_attempts + 1):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format=response_format_for(prompt_version),
            temperature=0,
            max_tokens=MAX_TOKENS,
        )
        choice = response.choices[0]
        answer = choice.message.content or ""

        if choice.finish_reason == "length":
            print(f"  attempt {attempt}/{max_attempts} cut off at {MAX_TOKENS} tokens")
            messages = messages + [
                {"role": "assistant", "content": answer.strip()},
                {
                    "role": "user",
                    "content": "Your answer was cut off before the JSON was complete. "
                               "Return the complete JSON only, without extra whitespace.",
                },
            ]
            continue

        try:
            return JobPosting.model_validate_json(answer)
        except ValidationError as error:
            print(f"  attempt {attempt}/{max_attempts} invalid: {error.error_count()} error(s)")
            messages = messages + [
                {"role": "assistant", "content": answer},
                {
                    "role": "user",
                    "content": f"Your JSON was invalid:\n{error}\n\nReturn the corrected JSON only.",
                },
            ]

    raise ExtractionError(f"No valid answer after {max_attempts} attempts")