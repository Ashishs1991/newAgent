# Job Research Agent

A deliberately small first agent: it decides what to search, inspects the results,
and returns a cited shortlist. It cannot apply for jobs or modify external systems.

## Run it

```bash
cd job-research-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set OPENAI_API_KEY and TAVILY_API_KEY

python agent.py "Find Lead AI Engineer jobs in Bengaluru and explain the best matches"
```

Output is **validated JSON** (`query_summary`, `matches[]`, optional `notes`) defined in
`job_research/schemas.py`. LangChain `response_format` enforces the schema on the
final structured result.

Configuration loads from `.env` via `python-dotenv`. Copy `.env.example` for every
variable name and default; never commit `.env`.

## Evaluation (Step 2)

Ten sample queries live in `eval/queries.json`. Deterministic checks (URL present,
duplicate URLs, max five matches) are in `job_research/evaluation.py`.

```bash
# Free — no API calls
python eval/run_eval.py --fixture

# Live — defaults to 1 query to save credits
python eval/run_eval.py --live --limit 1

# One query by id
python eval/run_eval.py --live --query-id bengaluru-ai-engineer-one
```

```bash
python -c "from tests.test_evaluation import test_eval_passes_for_valid_response, test_eval_fails_on_duplicate_urls; test_eval_passes_for_valid_response(); test_eval_fails_on_duplicate_urls()"
```

## What to watch

In the trace, follow this loop:

```text
request -> model chooses a search -> tool returns evidence -> model decides
whether to search again -> final cited answer
```

The code hard-limits each run (defaults in `.env.example`: five model calls, two
search calls, 1,200 tokens per model response). Structured output may need one extra
model turn after Tavily; if limits are too low, the agent stops before JSON is ready.

## Learning increments

1. ~~Structured result schema and ten test queries~~ (see `job_research/schemas.py`, `eval/`).
2. Add a second tool that reads a selected company job page.
3. Replace the prebuilt loop with LangGraph nodes and explicit state.
4. Add persistence, retries, human approval, and richer offline evaluations only when
   the earlier version gives you a concrete failure to solve.

Do not add LinkedIn scraping. LinkedIn restricts automated scraping, and its job
APIs generally require approved partner access.
