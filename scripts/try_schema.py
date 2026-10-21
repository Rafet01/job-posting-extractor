"""Play around with the JobPosting schema: valid and invalid examples."""

import json

from pydantic import ValidationError

from extractor.schema import JobPosting

# 1. A valid posting, built from a Python dict.
data = {
    "company": "D ONE",
    "role_title": "Intern LLM-Based Information Extraction",
    "location": "Zürich",
    "workload_min": 80,
    "workload_max": 100,
    "duration_months": 6,
    "start": "February 2027",
    "german_level": "plus",
    "english_required": True,
    "degree_level": "bachelor_ok",
    "is_internship": True,
    "required_skills": ["Python", " SQL ", "python", "Git"],
}
posting = JobPosting(**data)
print("Valid posting:")
print(posting)
print("Skills after cleaning:", posting.required_skills)

# 2. Invalid values: Pydantic tells you exactly which field is wrong and why.
bad_examples = [
    {**data, "german_level": "fluent"},
    {**data, "workload_min": 100, "workload_max": 80},
]
for bad in bad_examples:
    try:
        JobPosting(**bad)
    except ValidationError as error:
        print("\nInvalid posting:")
        print(error)

# 3. Parsing a JSON string, which is what the LLM will give us in step 3.
llm_answer = json.dumps(data)
parsed = JobPosting.model_validate_json(llm_answer)
print("\nParsed from JSON:", parsed.company, parsed.workload_min, parsed.workload_max)

# 4. The JSON Schema Pydantic generates; we will send this to the LLM later.
print("\nJSON Schema (first 400 characters):")
print(json.dumps(JobPosting.model_json_schema(), indent=2)[:400])