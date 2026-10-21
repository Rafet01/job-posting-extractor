"""LLM client and the extraction call, with retries on invalid answers."""

import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from extractor.prompts import build_messages
from extractor.schema import JobPosting

load_dotenv()


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
            response_format={"type": "json_object"},
            temperature=0,
        )
        answer = response.choices[0].message.content or ""

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