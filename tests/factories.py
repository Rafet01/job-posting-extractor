"""Builders for valid test data, so each test only spells out what it changes."""

from extractor.schema import JobPosting


def posting_fields(**changes: object) -> dict:
    """The fields of a small valid posting, with optional replacements."""
    fields = dict(company="Example", role_title="Data Intern", german_level="none",
                  english_required=False, degree_level="unknown", is_internship=True)
    return fields | changes


def posting(**changes: object) -> JobPosting:
    """A small valid posting, with optional replacements."""
    return JobPosting.model_validate(posting_fields(**changes))
