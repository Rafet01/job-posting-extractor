"""Pydantic schema for the fields we extract from a job posting."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GermanLevel = Literal["none", "plus", "required"]
DegreeLevel = Literal["bachelor_ok", "master_only", "graduate_only", "unknown"]


class JobPosting(BaseModel):
    """Structured information extracted from one job posting."""

    # Reject fields the LLM invents that are not in the schema.
    model_config = ConfigDict(extra="forbid")

    company: str = Field(description="Name of the hiring company.")
    role_title: str = Field(description="Job title as written in the posting.")
    location: str = Field(description="City of the workplace, e.g. 'Zürich'.")
    workload_min: int | None = Field(
        default=None,
        ge=10,
        le=100,
        description="Minimum workload in percent, e.g. 80 for '80-100%'. Null if not stated.",
    )
    workload_max: int | None = Field(
        default=None,
        ge=10,
        le=100,
        description="Maximum workload in percent, e.g. 100 for '80-100%'. Null if not stated.",
    )
    duration_months: int | None = Field(
        default=None,
        ge=1,
        le=24,
        description="Duration of the position in months. Null if not stated.",
    )
    start: str | None = Field(
        default=None,
        description="Start date or period as written, e.g. 'February 2027' or 'asap'. Null if not stated.",
    )
    german_level: GermanLevel = Field(
        description="'required' if German is mandatory, 'plus' if it is nice to have, 'none' if not mentioned.",
    )
    english_required: bool = Field(description="True if English is explicitly required.")
    degree_level: DegreeLevel = Field(
        description=(
            "'bachelor_ok' if bachelor students can apply, 'master_only' if only master students, "
            "'graduate_only' if a finished degree is required, 'unknown' if not stated."
        ),
    )
    is_internship: bool = Field(
        description="True for an internship/Praktikum, False for a permanent job or working student role.",
    )
    required_skills: list[str] = Field(
        default_factory=list,
        description="Mandatory technical skills, lowercase, e.g. ['python', 'sql'].",
    )

    @field_validator("required_skills")
    @classmethod
    def normalize_skills(cls, skills: list[str]) -> list[str]:
        """Lowercase and strip each skill, drop empty ones and duplicates."""
        cleaned: list[str] = []
        for skill in skills:
            skill = skill.strip().lower()
            if skill and skill not in cleaned:
                cleaned.append(skill)
        return cleaned

    @model_validator(mode="after")
    def check_workload_range(self) -> "JobPosting":
        """A minimum workload can never be higher than the maximum."""
        if (
            self.workload_min is not None
            and self.workload_max is not None
            and self.workload_min > self.workload_max
        ):
            raise ValueError("workload_min cannot be greater than workload_max")
        return self