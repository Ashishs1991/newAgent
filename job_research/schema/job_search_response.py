from pydantic import BaseModel, Field, field_validator

from job_research.schema.job_match import JobMatch


class JobSearchResponse(BaseModel):
    """Validated agent output for a single user job search request."""

    query_summary: str = Field(
        description="How the agent interpreted the user's role, location, and constraints."
    )
    matches: list[JobMatch] = Field(
        default_factory=list,
        max_length=5,
        description="Up to five deduplicated job matches.",
    )
    notes: str | None = Field(
        default=None,
        description="Optional caveats about search coverage or evidence quality.",
    )

    @field_validator("query_summary")
    @classmethod
    def strip_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query_summary must not be empty")
        return cleaned
