from dataclasses import dataclass
from urllib.parse import urlparse

from job_research.schema import JobSearchResponse

MAX_MATCHES = 5

CAREER_HOST_OR_PATH_MARKERS = (
    "careers.",
    "jobs.",
    "/careers",
    "/jobs",
    "myworkdayjobs.com",
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class EvaluationReport:
    query_id: str
    checks: tuple[CheckResult, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


@dataclass(frozen=True)
class HeuristicReport:
    """Lightweight signals — not a substitute for human quality review."""

    query_id: str
    checks: tuple[CheckResult, ...]


def empty_manual_review_template() -> dict:
    """Scores you fill after reading LangSmith + URLs (1–5 or pass/fail notes)."""
    return {
        "relevant_matches": None,
        "listing_likely_open": None,
        "source_supports_each_field": None,
        "sensible_tool_choices": None,
        "search_efficiency": None,
        "grounded_in_evidence_not_full_jd": None,
        "reviewer_notes": "",
    }


def is_likely_official_career_url(url: str) -> bool:
    parsed = urlparse(url.strip().lower())
    if not parsed.netloc:
        return False
    if "linkedin.com" in parsed.netloc:
        return False
    blob = f"{parsed.netloc}{parsed.path}"
    return any(marker in blob for marker in CAREER_HOST_OR_PATH_MARKERS)


def evaluate_heuristics(query_id: str, response: JobSearchResponse) -> HeuristicReport:
    checks: list[CheckResult] = []
    if not response.matches:
        checks.append(
            CheckResult(
                name="official_career_page_ratio",
                passed=False,
                detail="no matches to score",
            )
        )
        return HeuristicReport(query_id=query_id, checks=tuple(checks))

    official = sum(1 for m in response.matches if is_likely_official_career_url(m.source_url))
    ratio = official / len(response.matches)
    checks.append(
        CheckResult(
            name="official_career_page_ratio",
            passed=ratio >= 0.5,
            detail=f"{official}/{len(response.matches)} URLs look like company career pages",
        )
    )
    return HeuristicReport(query_id=query_id, checks=tuple(checks))


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip().lower())
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def evaluate_response(query_id: str, response: JobSearchResponse) -> EvaluationReport:
    """Deterministic structural checks (shape and hygiene — not LLM quality)."""
    checks: list[CheckResult] = []

    count = len(response.matches)
    checks.append(
        CheckResult(
            name="match_count_within_limit",
            passed=count <= MAX_MATCHES,
            detail=f"{count} matches (max {MAX_MATCHES})",
        )
    )

    missing_urls: list[str] = []
    invalid_urls: list[str] = []
    for index, match in enumerate(response.matches, start=1):
        url = match.source_url.strip()
        if not url:
            missing_urls.append(str(index))
            continue
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            invalid_urls.append(str(index))

    checks.append(
        CheckResult(
            name="each_match_has_http_source",
            passed=not missing_urls and not invalid_urls,
            detail=(
                "all URLs valid"
                if not missing_urls and not invalid_urls
                else f"missing={missing_urls or '-'}, invalid={invalid_urls or '-'}"
            ),
        )
    )

    normalized = [_normalize_url(match.source_url) for match in response.matches]
    duplicate_count = len(normalized) - len(set(normalized))
    checks.append(
        CheckResult(
            name="no_duplicate_source_urls",
            passed=duplicate_count == 0,
            detail=f"{duplicate_count} duplicate URL(s) after normalization",
        )
    )

    empty_fields: list[str] = []
    for index, match in enumerate(response.matches, start=1):
        for field_name in ("title", "company", "location", "match_reason"):
            if not getattr(match, field_name).strip():
                empty_fields.append(f"{index}.{field_name}")

    checks.append(
        CheckResult(
            name="required_fields_present",
            passed=not empty_fields,
            detail="ok" if not empty_fields else ", ".join(empty_fields),
        )
    )

    checks.append(
        CheckResult(
            name="query_summary_present",
            passed=bool(response.query_summary.strip()),
            detail=response.query_summary[:80] + ("..." if len(response.query_summary) > 80 else ""),
        )
    )

    return EvaluationReport(query_id=query_id, checks=tuple(checks))
