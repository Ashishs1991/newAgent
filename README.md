# Job Research Agent

A deliberately small first agent: it decides what to search, inspects the results,
and returns a cited shortlist. It cannot apply for jobs or modify external systems.

## Run it

```bash
cd job-research-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export OPENAI_API_KEY="..."
export TAVILY_API_KEY="..."
export OPENAI_MODEL="gpt-5-mini"  # optional
export LANGSMITH_TRACING="true"   # optional
export LANGSMITH_API_KEY="..."    # optional
export LANGSMITH_PROJECT="job-research-agent"  # optional

python agent.py "Find Lead AI Engineer jobs in Bengaluru and explain the best matches"
```

## What to watch

In the trace, follow this loop:

```text
request -> model chooses a search -> tool returns evidence -> model decides
whether to search again -> final cited answer
```

The code hard-limits each run to four model calls, three search calls, and 1,200
tokens per model response. `MAX_OUTPUT_TOKENS` changes the per-response limit; it
is not a whole-run token budget.

## Learning increments

1. Add a structured result schema and test ten known job queries.
2. Add a second tool that reads a selected company job page.
3. Replace the prebuilt loop with LangGraph nodes and explicit state.
4. Add persistence, retries, human approval, and offline evaluations only when
   the earlier version gives you a concrete failure to solve.

Do not add LinkedIn scraping. LinkedIn restricts automated scraping, and its job
APIs generally require approved partner access.
