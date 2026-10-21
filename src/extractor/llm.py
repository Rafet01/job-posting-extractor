"""LLM client and the extraction call."""

import os

from dotenv import load_dotenv
from openai import OpenAI

from extractor.prompts import build_messages
from extractor.schema import JobPosting

load_dotenv()


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
) -> JobPosting:
    """Send one posting to the LLM and validate the answer with Pydantic."""
    response = client.chat.completions.create(
        model=model,
        messages=build_messages(posting_text, prompt_version),
        response_format={"type": "json_object"},
        temperature=0,
    )
    answer = response.choices[0].message.content
    return JobPosting.model_validate_json(answer)