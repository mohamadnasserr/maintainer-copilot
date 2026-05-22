import json
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.infra.rag import RagPipeline

GOLDEN_PATH = Path("evals/rag_golden.jsonl")
THRESHOLDS_PATH = Path("evals/eval_thresholds.yaml")
REPORT_PATH = Path("eval_report.json")


def load_golden_set(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing golden set file: {path}")

    examples: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                example = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc

            examples.append(example)

    return examples


def load_thresholds(path: Path) -> dict[str, float]:
    if not path.exists():
        raise FileNotFoundError(f"Missing thresholds file: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict) or "rag" not in data:
        raise ValueError("Threshold file must contain a top-level 'rag' section.")

    rag = data["rag"]

    required_keys = [
        "min_hit_at_1",
        "min_hit_at_3",
        "min_hit_at_5",
        "min_mrr_at_10",
    ]

    for key in required_keys:
        if key not in rag:
            raise ValueError(f"Missing threshold: rag.{key}")

        value = float(rag[key])
        if value <= 0:
            raise ValueError(f"Threshold rag.{key} must be greater than zero.")

    thresholds = {
        "hit@1": float(rag["min_hit_at_1"]),
        "hit@3": float(rag["min_hit_at_3"]),
        "hit@5": float(rag["min_hit_at_5"]),
        "mrr@10": float(rag["min_mrr_at_10"]),
    }

    # Optional generation thresholds. If they are not present, the script reports
    # generation metrics but does not fail on them.
    optional_mapping = {
        "min_answer_keyword_coverage": "answer_keyword_coverage",
        "min_source_url_coverage": "source_url_coverage",
        "min_faithfulness_proxy": "faithfulness_proxy",
    }

    for yaml_key, metric_name in optional_mapping.items():
        if yaml_key in rag:
            value = float(rag[yaml_key])
            if value <= 0:
                raise ValueError(f"Threshold rag.{yaml_key} must be greater than zero.")
            thresholds[metric_name] = value

    return thresholds


def reciprocal_rank(
    retrieved_issue_numbers: list[int],
    expected_issue_numbers: list[int],
) -> float:
    expected = set(expected_issue_numbers)

    for rank, issue_number in enumerate(retrieved_issue_numbers, start=1):
        if issue_number in expected:
            return 1.0 / rank

    return 0.0


def keyword_coverage(answer: str, expected_phrases: list[str]) -> float:
    if not expected_phrases:
        return 1.0

    answer_lower = answer.lower()
    matched = 0

    for phrase in expected_phrases:
        if phrase.lower() in answer_lower:
            matched += 1

    return matched / len(expected_phrases)


def source_url_coverage(chunks: list[Any]) -> float:
    if not chunks:
        return 0.0

    source_urls = [chunk.source_url for chunk in chunks if chunk.source_url]

    if not source_urls:
        return 0.0

    github_urls = [
        url for url in source_urls
        if url.startswith("https://github.com/pandas-dev/pandas/issues/")
    ]

    return len(github_urls) / len(source_urls)


def faithfulness_proxy(answer: str, chunks: list[Any]) -> float:
    """
    Lightweight CPU-only faithfulness proxy.

    This is not a judge model. It checks whether the generated answer overlaps
    with retrieved source text and includes source-grounded issue references.
    """
    if not answer or not chunks:
        return 0.0

    answer_lower = answer.lower()

    issue_reference_score = 1.0 if "pandas issue #" in answer_lower else 0.0

    chunk_titles = [chunk.title.lower() for chunk in chunks[:3]]
    title_hits = sum(1 for title in chunk_titles if title and title[:30] in answer_lower)
    title_score = title_hits / max(len(chunk_titles), 1)

    source_text = " ".join(chunk.text.lower() for chunk in chunks[:3])
    answer_tokens = {
        token
        for token in answer_lower.replace(".", " ").replace(",", " ").split()
        if len(token) >= 5
    }

    source_tokens = {
        token
        for token in source_text.replace(".", " ").replace(",", " ").split()
        if len(token) >= 5
    }

    if not answer_tokens:
        token_overlap_score = 0.0
    else:
        token_overlap_score = len(answer_tokens.intersection(source_tokens)) / len(answer_tokens)

    return round(
        0.40 * issue_reference_score
        + 0.30 * title_score
        + 0.30 * token_overlap_score,
        4,
    )


def evaluate() -> dict[str, Any]:
    rag = RagPipeline(top_k=10)
    examples = load_golden_set(GOLDEN_PATH)

    results: list[dict[str, Any]] = []

    hit_at_1 = 0
    hit_at_3 = 0
    hit_at_5 = 0
    mrr_total = 0.0

    answer_keyword_coverage_total = 0.0
    source_url_coverage_total = 0.0
    faithfulness_proxy_total = 0.0

    for example in examples:
        question = example["question"]
        expected_issue_numbers = example["expected_issue_numbers"]
        ideal_answer_contains = example.get("ideal_answer_contains", [])

        answer, chunks = rag.answer(question)

        retrieved_issue_numbers: list[int] = []
        retrieved_titles: list[str] = []

        for chunk in chunks:
            issue_number = chunk.metadata.get("issue_number")
            if issue_number is not None:
                retrieved_issue_numbers.append(int(issue_number))
            retrieved_titles.append(chunk.title)

        expected_set = set(expected_issue_numbers)

        top_1 = retrieved_issue_numbers[:1]
        top_3 = retrieved_issue_numbers[:3]
        top_5 = retrieved_issue_numbers[:5]

        example_hit_at_1 = bool(expected_set.intersection(top_1))
        example_hit_at_3 = bool(expected_set.intersection(top_3))
        example_hit_at_5 = bool(expected_set.intersection(top_5))
        example_mrr = reciprocal_rank(retrieved_issue_numbers, expected_issue_numbers)

        example_answer_keyword_coverage = keyword_coverage(answer, ideal_answer_contains)
        example_source_url_coverage = source_url_coverage(chunks)
        example_faithfulness_proxy = faithfulness_proxy(answer, chunks)

        hit_at_1 += int(example_hit_at_1)
        hit_at_3 += int(example_hit_at_3)
        hit_at_5 += int(example_hit_at_5)
        mrr_total += example_mrr

        answer_keyword_coverage_total += example_answer_keyword_coverage
        source_url_coverage_total += example_source_url_coverage
        faithfulness_proxy_total += example_faithfulness_proxy

        results.append(
            {
                "id": example["id"],
                "question": question,
                "expected_issue_numbers": expected_issue_numbers,
                "retrieved_issue_numbers": retrieved_issue_numbers[:10],
                "retrieved_titles": retrieved_titles[:10],
                "hit@1": example_hit_at_1,
                "hit@3": example_hit_at_3,
                "hit@5": example_hit_at_5,
                "reciprocal_rank": example_mrr,
                "answer_keyword_coverage": round(example_answer_keyword_coverage, 4),
                "source_url_coverage": round(example_source_url_coverage, 4),
                "faithfulness_proxy": round(example_faithfulness_proxy, 4),
            }
        )

    total = len(examples)

    if total == 0:
        raise ValueError("Golden set is empty.")

    report = {
        "total_examples": total,
        "metrics": {
            "hit@1": round(hit_at_1 / total, 4),
            "hit@3": round(hit_at_3 / total, 4),
            "hit@5": round(hit_at_5 / total, 4),
            "mrr@10": round(mrr_total / total, 4),
            "answer_keyword_coverage": round(answer_keyword_coverage_total / total, 4),
            "source_url_coverage": round(source_url_coverage_total / total, 4),
            "faithfulness_proxy": round(faithfulness_proxy_total / total, 4),
        },
        "results": results,
    }

    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return report


def assert_thresholds(report: dict[str, Any], thresholds: dict[str, float]) -> None:
    metrics = report["metrics"]
    failures: list[str] = []

    for metric_name, minimum_value in thresholds.items():
        actual_value = float(metrics[metric_name])

        if actual_value < minimum_value:
            failures.append(
                f"{metric_name}={actual_value} is below threshold {minimum_value}"
            )

    if failures:
        formatted = "\n".join(f"- {failure}" for failure in failures)
        raise SystemExit(f"RAG evaluation failed:\n{formatted}")


def main() -> None:
    thresholds = load_thresholds(THRESHOLDS_PATH)
    report = evaluate()

    print("RAG evaluation complete")
    print(f"Total examples: {report['total_examples']}")
    print(json.dumps(report["metrics"], indent=2))
    print(f"Wrote report to {REPORT_PATH}")

    assert_thresholds(report, thresholds)

    print("RAG evaluation passed thresholds")


if __name__ == "__main__":
    main()