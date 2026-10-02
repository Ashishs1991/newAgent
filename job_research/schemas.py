from pydantic import BaseModel, Field, field_validator


class JobMatch(BaseModel):
    """One job listing supported by search evidence."""

    title: str = Field(description="Job title from the listing or snippet.")
    company: str = Field(description="Hiring company name.")
    location: str = Field(description="City, region, or remote policy stated in evidence.")
    source_url: str = Field(description="Public URL for the listing (career page preferred).")
    match_reason: str = Field(
        description="Short explanation of why this listing matches the user request."
    )
    uncertain_fields: list[str] = Field(
        default_factory=list,
        description="Field names or facts that are missing, inferred, or stale.",
    )

    @field_validator("title", "company", "location", "match_reason", "source_url")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned


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
