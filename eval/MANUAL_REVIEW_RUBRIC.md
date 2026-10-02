# Manual quality review (baseline)

Structural eval (`evaluate_response`) only checks **shape**: URLs present, no duplicates,
field non-empty, max five matches. It does **not** know if the job is good.

After `python eval/run_baseline.py`, open each run in **LangSmith** and the cited URLs.
Edit `manual_review` in the saved JSON (or copy into `AshishNotes.md`).

## LangSmith URL for `reviewer_notes`

1. Open [LangSmith](https://smith.langchain.com/) → project **`job-research-agent`** (or your `LANGSMITH_PROJECT`).
2. In **Runs** / **Traces**, pick the run that matches this query and time (sort by newest).
3. Click the run so the trace waterfall opens.
4. Copy the **browser address bar** URL (looks like  
   `https://smith.langchain.com/.../projects/p/.../r/...` or `/public/.../r/...`).
5. Paste that full URL into `manual_review.reviewer_notes` in the baseline JSON.

You do **not** need to send the URL to anyone unless sharing with a reviewer — it is for **your** audit trail (reopen the exact trace later). Optional: add one line which job URL you spot-checked.

## Rubric (use pass/fail or 1–5)

| Field | Question |
|-------|----------|
| **relevant_matches** | Does the role/location/company match what the user asked? |
| **listing_likely_open** | Does the page look like an active posting (not obviously closed)? |
| **source_supports_each_field** | Can you see title/company/location in the **source** or Tavily snippet? |
| **sensible_tool_choices** | Were Tavily queries reasonable? Any pointless second search? |
| **search_efficiency** | Could one search have been enough? |
| **grounded_in_evidence_not_full_jd** | Is the answer honest about snippet-only evidence (no fake JD details)? |

## Interview framing (30 seconds)

> We split evaluation into **structural** (automated, cheap, CI-friendly) and **quality**
> (human or later LLM-as-judge). Structural catches broken URLs and schema violations;
> quality catches wrong job title, stale listings, and hallucinated requirements.
> We record a **baseline** before adding tools so we can prove the second tool improved
> grounded answers, not just JSON validity.

## Regression cases

When a run fails structurally or is a good **quality** failure example, save it under
`eval/regression/<query_id>.json` using:

```bash
python eval/run_baseline.py --limit 1 --query-id bengaluru-lead-ai \
  --save-regression bengaluru-lead-ai
```

Re-run the same query after code changes and compare metrics + manual_review.
