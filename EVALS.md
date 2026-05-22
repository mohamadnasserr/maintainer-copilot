# Evals — Maintainers Copilot

## Evaluation Goal

The goal of evaluation is to make sure the RAG system retrieves the correct pandas maintainer context for known questions.

The current evaluation focuses on retrieval quality. Generation quality can be added later with a judge model or manual scoring.

## Files

```text
evals/rag_golden.jsonl
evals/run_rag_eval.py
evals/eval_thresholds.yaml
eval_report.json

Golden Set

The RAG golden set is stored in:

evals/rag_golden.jsonl

Each line is one JSON object.

Example:

{
  "id": "rag-001",
  "question": "What pandas issue discusses groupby.value_counts performance?",
  "expected_issue_numbers": [51750],
  "ideal_answer_contains": ["groupby.value_counts", "performance"]
}

The important field for retrieval evaluation is:

expected_issue_numbers

This tells the eval script which pandas issue should appear in the retrieved results.

Current Golden Examples

The current initial golden set has 5 examples.

It tests questions about:

groupby.value_counts performance
groupby().first() documentation
GroupBy.agg() and numeric_only
groupby cumulative operations returning Float64
df.corrupt() accessor proposal

The final target is to expand this toward 25 examples.

Metrics

The eval script measures:

hit@1

Whether the expected issue appears as the first retrieved result.

hit@3

Whether the expected issue appears in the top 3 retrieved results.

hit@5

Whether the expected issue appears in the top 5 retrieved results.

mrr@10

Mean Reciprocal Rank over the top 10 results.

This gives a higher score when the correct issue appears closer to rank 1.

Example:

Correct issue at rank 1 → reciprocal rank = 1.0
Correct issue at rank 2 → reciprocal rank = 0.5
Correct issue at rank 5 → reciprocal rank = 0.2
Missing from top 10 → reciprocal rank = 0.0
Current Results

Current metrics from the 5-example golden set:

hit@1  = 0.60
hit@3  = 0.80
hit@5  = 0.80
mrr@10 = 0.72

These are written to:

eval_report.json
Thresholds

Thresholds are stored in:

evals/eval_thresholds.yaml

Current thresholds:

rag:
  min_hit_at_1: 0.50
  min_hit_at_3: 0.70
  min_hit_at_5: 0.70
  min_mrr_at_10: 0.60

The eval fails if any metric drops below the threshold.

How to Run

Make sure Postgres is running and the RAG chunks have been ingested.

Start infrastructure:

docker compose up -d db vault redis

Run the eval:

python evals/run_rag_eval.py

Expected output:

RAG evaluation complete
Total examples: 5
{
  "hit@1": 0.6,
  "hit@3": 0.8,
  "hit@5": 0.8,
  "mrr@10": 0.72
}
Wrote report to eval_report.json
RAG evaluation passed thresholds
What the Eval Proves

The eval proves that the retriever can locate expected pandas issue context for known questions.

For example:

Question:
What pandas issue discusses groupby.value_counts performance?

Expected:
Issue #51750

Correct behavior:
Issue #51750 appears in the retrieved results.
Current Limitations

Current eval limitations:

Only 5 examples so far.
Retrieval-only metrics are implemented.
Generation metrics such as faithfulness and answer relevancy are not implemented yet.
No RAGAS or judge model is currently integrated.
eval_report.json is generated locally but not yet uploaded to MinIO.
CI wiring is not fully implemented yet.
Next Improvements

Planned improvements:

Expand the golden set from 5 to 25 examples.
Add generation quality checks.
Add a frozen judge model or manual scoring for answer faithfulness.
Store eval_report.json in MinIO.
Run evals/run_rag_eval.py in CI.
Fail CI if thresholds are not met.
Why This Matters

The project should not rely only on manual testing or a nice-looking chatbot.

The eval gives a measurable answer to:

Did retrieval get better or worse?

This supports the assignment requirement that every retrieval decision should be backed by a number.
