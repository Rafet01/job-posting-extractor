"""The JobPosting schema accepts valid extractions and rejects everything else."""

import pytest
from pydantic import ValidationError

from extractor.schema import JobPosting
from tests.factories import posting, posting_fields


def test_optional_fields_default_to_empty() -> None:
    """A posting that states nothing optional gets null values and empty lists."""
    result = posting()
    assert result.locations == [] and result.required_skills == []
    assert result.workload_min is result.workload_max is result.duration_months is result.start is None


@pytest.mark.parametrize("field", ["company", "role_title", "german_level", "english_required",
                                   "degree_level", "is_internship"])
def test_missing_required_field_is_rejected(field: str) -> None:
    """Fields without a sensible default must be present in every answer."""
    fields = posting_fields()
    del fields[field]
    with pytest.raises(ValidationError, match=field):
        JobPosting.model_validate(fields)


@pytest.mark.parametrize("field, value", [
    ("german_level", "fluent"),
    ("german_level", "Required"),
    ("degree_level", "phd_only"),
])
def test_value_outside_the_allowed_categories_is_rejected(field: str, value: str) -> None:
    """Category fields accept only their exact labels, so typos cannot hide in the results."""
    with pytest.raises(ValidationError, match=field):
        posting(**{field: value})


@pytest.mark.parametrize("field, value", [
    ("workload_min", 9), ("workload_min", 101), ("workload_max", 0), ("workload_max", 120),
    ("duration_months", 0), ("duration_months", 25),
])
def test_number_outside_its_range_is_rejected(field: str, value: int) -> None:
    """Workload is a percentage from 10 to 100 and duration lies between 1 and 24 months."""
    with pytest.raises(ValidationError, match=field):
        posting(**{field: value})


def test_minimum_workload_above_maximum_is_rejected() -> None:
    """A range like 100-80% is contradictory."""
    with pytest.raises(ValidationError, match="workload_min cannot be greater than workload_max"):
        posting(workload_min=100, workload_max=80)


def test_one_sided_or_exact_workload_is_accepted() -> None:
    """'At least 80%' fills only the minimum, '100%' fills both bounds."""
    assert posting(workload_min=80).workload_max is None
    assert posting(workload_min=100, workload_max=100).workload_min == 100


def test_field_outside_the_schema_is_rejected() -> None:
    """Fields the LLM invents are an error, not silently dropped."""
    with pytest.raises(ValidationError, match="salary"):
        posting(salary="CHF 2500")


@pytest.mark.parametrize("field", ["company", "role_title"])
@pytest.mark.parametrize("value", ["", "   "])
def test_empty_company_or_title_is_rejected(field: str, value: str) -> None:
    """An answer without a company name or title is retried, not cached."""
    with pytest.raises(ValidationError, match=f"{field}\n.*must not be empty"):
        posting(**{field: value})


def test_blank_check_does_not_change_the_json_schema() -> None:
    """The check is Python-only: the schema sent in the prompt has no minLength."""
    assert "minLength" not in str(JobPosting.model_json_schema())


def test_skills_are_lowercased_stripped_and_deduplicated() -> None:
    """Skills are compared as sets later, so spelling variants of one skill collapse."""
    result = posting(required_skills=[" Python", "SQL ", "python", "", "  ", "Power BI"])
    assert result.required_skills == ["python", "sql", "power bi"]
