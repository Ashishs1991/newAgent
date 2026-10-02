from job_research.evaluation import evaluate_response
from job_research.schema import JobMatch, JobSearchResponse


def test_eval_passes_for_valid_response() -> None:
    response = JobSearchResponse(
        query_summary="AI Engineer in Bengaluru at NVIDIA",
        matches=[
            JobMatch(
                title="Developer Technology Engineer – AI",
                company="NVIDIA",
                location="Bengaluru, India",
                source_url="https://jobs.nvidia.com/careers/job/893397112810",
                match_reason="AI engineering role in Bengaluru on NVIDIA careers site.",
            )
        ],
    )
    report = evaluate_response("sample", response)
    assert report.passed


def test_eval_fails_on_duplicate_urls() -> None:
    url = "https://jobs.example.com/role/1"
    response = JobSearchResponse(
        query_summary="Test query",
        matches=[
            JobMatch(
                title="Role A",
                company="Co",
                location="Loc",
                source_url=url,
                match_reason="reason a",
            ),
            JobMatch(
                title="Role B",
                company="Co",
                location="Loc",
                source_url=url,
                match_reason="reason b",
            ),
        ],
    )
    report = evaluate_response("dup", response)
    assert not report.passed
    assert any(check.name == "no_duplicate_source_urls" and not check.passed for check in report.checks)
