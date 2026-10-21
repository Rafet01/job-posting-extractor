"""Prompt variants for the extraction task."""

import json

from extractor.schema import JobPosting

SYSTEM_PROMPT_V1 = """You extract structured information from job postings.
Answer with one JSON object that follows this JSON Schema exactly:

{schema}

Rules:
- Use null when information is not stated in the posting.
- Do not add fields that are not in the schema.
- Answer with JSON only, no explanation."""

PROMPTS = {
    "v1": SYSTEM_PROMPT_V1,
}


def build_messages(posting_text: str, version: str = "v1") -> list[dict[str, str]]:
    """Build the chat messages for one posting with the given prompt version."""
    schema = json.dumps(JobPosting.model_json_schema(), indent=2)
    system_prompt = PROMPTS[version].format(schema=schema)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": posting_text},
    ]