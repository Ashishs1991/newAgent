#!/usr/bin/env python3
"""Record a live baseline: structural checks, metrics, and manual review slots."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from job_research import JobResearchAgent, Settings
from job_research.evaluation import (
    empty_manual_review_template,
    evaluate_heuristics,
    evaluate_response,
)

QUERIES_PATH = Path(__file__).resolve().parent / "queries.json"
BASELINE_IDS_PATH = Path(__file__).resolve().parent / "baseline_queries.json"
RUNS_DIR = Path(__file__).resolve().parent / "baseline" / "runs"
REGRESSION_DIR = Path(__file__).resolve().parent / "regression"


def load_queries() -> dict[str, dict[str, str]]:
    items = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    return {item["id"]: item for item in items}


def checks_to_dict(checks) -> list[dict]:
    return [{"name": c.name, "passed": c.passed, "detail": c.detail} for c in checks]


def run_record(agent: JobResearchAgent, settings: Settings, query_id: str, query: str) -> dict:
    try:
        run = agent.run(query)
    except RuntimeError as exc:
        return {
            "query_id": query_id,
            "query": query,
            "error": str(exc),
            "structural_pass": False,
            "structural_checks": [],
            "heuristic_checks": [],
            "metrics": None,
            "response": None,
            "manual_review": empty_manual_review_template(),
            "langsmith": {
                "project": settings.langsmith_project,
                "hint": "If a trace exists before failure, paste its URL in reviewer_notes",
            },
        }

    structural = evaluate_response(query_id, run.response)
    heuristics = evaluate_heuristics(query_id, run.response)
    m = run.metrics
    return {
        "query_id": query_id,
        "query": query,
        "structural_pass": structural.passed,
        "structural_checks": checks_to_dict(structural.checks),
        "heuristic_checks": checks_to_dict(heuristics.checks),
        "metrics": {
            "latency_seconds": run.latency_seconds,
            "agent_model_calls": m.agent_model_calls,
            "agent_tool_calls": m.agent_tool_calls,
            "fallback_synthesis_calls": m.fallback_synthesis_calls,
            "used_fallback_synthesis": run.used_fallback_synthesis,
            "total_input_tokens": m.total_input_tokens,
            "total_output_tokens": m.total_output_tokens,
            "total_tokens": m.total_tokens,
            "approximate_openai_usd_agent_loop_only": m.approximate_openai_usd,
            "cost_note": (
                "USD estimate covers token usage on agent-loop AIMessages only; "
                "fallback synthesis and Tavily are extra. Set OPENAI_INPUT_USD_PER_1M "
                "in .env for estimates."
            ),
        },
        "response": run.response.model_dump(),
        "manual_review": empty_manual_review_template(),
        "langsmith": {
            "project": settings.langsmith_project,
            "hint": "Open this run in LangSmith and paste run URL into manual_review.reviewer_notes",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Record eval baseline before Step 3.")
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="How many baseline queries to run (default: 5 from baseline_queries.json).",
    )
    parser.add_argument(
        "--query-id",
        action="append",
        dest="query_ids",
        help="Run specific query id(s); can repeat flag.",
    )
    parser.add_argument(
        "--save-regression",
        metavar="QUERY_ID",
        help="After run, copy that query result to eval/regression/<id>.json if structural_pass is false.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: eval/baseline/runs/<timestamp>.json).",
    )
    args = parser.parse_args()

    catalog = load_queries()
    if args.query_ids:
        ids = args.query_ids
    else:
        ids = json.loads(BASELINE_IDS_PATH.read_text(encoding="utf-8"))[: max(args.limit, 0)]

    settings = Settings.from_env()
    agent = JobResearchAgent(settings)

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    REGRESSION_DIR.mkdir(parents=True, exist_ok=True)

    runs: list[dict] = []
    for query_id in ids:
        if query_id not in catalog:
            raise SystemExit(f"Unknown query id {query_id!r}")
        print(f"Running {query_id}...")
        record = run_record(agent, settings, query_id, catalog[query_id]["query"])
        if record.get("error"):
            print(f"  ERROR: {record['error']}")
        elif record["structural_pass"]:
            print("  structural PASS")
        else:
            print("  structural FAIL")
        runs.append(record)

    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "settings_snapshot": {
            "openai_model": settings.openai_model,
            "max_output_tokens": settings.max_output_tokens,
            "max_model_calls": settings.max_model_calls,
            "max_tool_calls": settings.max_tool_calls,
            "tavily_max_results": settings.tavily_max_results,
            "openai_reasoning_effort": settings.openai_reasoning_effort,
        },
        "runs": runs,
        "next_steps": [
            "Fill manual_review for each run (see eval/MANUAL_REVIEW_RUBRIC.md).",
            "Save at least one weak run under eval/regression/ with --save-regression.",
        ],
    }

    out = args.output
    if out is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = RUNS_DIR / f"baseline_{stamp}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")

    structural_pass = sum(1 for r in runs if r.get("structural_pass"))
    errors = sum(1 for r in runs if r.get("error"))
    print(f"Structural pass: {structural_pass}/{len(runs)} ({errors} run error(s))")

    if args.save_regression:
        match = next((r for r in runs if r["query_id"] == args.save_regression), None)
        if match is None:
            raise SystemExit(f"Query {args.save_regression!r} was not in this batch.")
        reg_path = REGRESSION_DIR / f"{args.save_regression}.json"
        reg_path.write_text(json.dumps(match, indent=2), encoding="utf-8")
        print(f"Saved regression case: {reg_path}")


if __name__ == "__main__":
    main()
