import argparse
import hashlib
import json
import re
from pathlib import Path

DEFAULT_INPUT = Path("data/raw/pandas_closed_issues.json")
DEFAULT_OUTPUT = Path("data/processed/pandas_chunks.jsonl")
DEFAULT_REPO = "pandas-dev/pandas"
MAX_CHARS = 2200
OVERLAP_CHARS = 250


def clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def labels_for(issue: dict[str, object]) -> list[str]:
    labels = issue.get("labels", [])
    if not isinstance(labels, list):
        return []
    names: list[str] = []
    for label in labels:
        if isinstance(label, dict) and isinstance(label.get("name"), str):
            names.append(label["name"])
    return names


def stable_chunk_id(issue_number: object, chunk_index: int, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"pandas-issue-{issue_number}-chunk-{chunk_index:03d}-{digest}"


def split_markdownish(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text] if text else []

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        while len(paragraph) > max_chars:
            cut = paragraph.rfind(" ", 0, max_chars)
            if cut < max_chars // 2:
                cut = max_chars
            chunks.append(paragraph[:cut].strip())
            paragraph = paragraph[max(0, cut - overlap_chars):].strip()

        current = paragraph

    if current:
        chunks.append(current)

    if overlap_chars <= 0 or len(chunks) <= 1:
        return chunks

    with_overlap = [chunks[0]]
    for previous, chunk in zip(chunks, chunks[1:]):
        prefix = previous[-overlap_chars:].strip()
        with_overlap.append(f"{prefix}\n\n{chunk}".strip())
    return with_overlap


def issue_to_chunks(
    issue: dict[str, object],
    repo: str,
    max_chars: int,
    overlap_chars: int,
) -> list[dict[str, object]]:
    number = issue.get("number")
    title = clean_text(issue.get("title"))
    body = clean_text(issue.get("body"))
    if not title and not body:
        return []

    full_text = f"# {title}\n\n{body}".strip()
    raw_chunks = split_markdownish(full_text, max_chars=max_chars, overlap_chars=overlap_chars)
    records: list[dict[str, object]] = []
    label_names = labels_for(issue)

    for index, chunk in enumerate(raw_chunks):
        records.append(
            {
                "id": stable_chunk_id(number, index, chunk),
                "repo": repo,
                "source_url": issue.get("html_url", ""),
                "title": title or f"Issue {number}",
                "body": chunk,
                "text": chunk,
                "metadata": {
                    "source_type": "github_issue",
                    "kind": "closed_issue",
                    "issue_number": number,
                    "chunk_index": index,
                    "chunk_count": len(raw_chunks),
                    "state": issue.get("state"),
                    "labels": label_names,
                    "created_at": issue.get("created_at"),
                    "updated_at": issue.get("updated_at"),
                    "closed_at": issue.get("closed_at"),
                    "author": (issue.get("user") or {}).get("login") if isinstance(issue.get("user"), dict) else None,
                    "comments": issue.get("comments", 0),
                },
            }
        )

    return records


def load_issues(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run `python scripts/fetch_pandas_corpus.py --limit 100` first."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected {path} to contain a JSON list of GitHub issues.")
    return [item for item in data if isinstance(item, dict)]


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert fetched pandas issues into RAG-ready JSONL chunks.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--max-chars", type=int, default=MAX_CHARS)
    parser.add_argument("--overlap-chars", type=int, default=OVERLAP_CHARS)
    args = parser.parse_args()

    issues = load_issues(args.input)
    records: list[dict[str, object]] = []
    for issue in issues:
        if "pull_request" in issue:
            continue
        records.extend(
            issue_to_chunks(
                issue,
                repo=args.repo,
                max_chars=args.max_chars,
                overlap_chars=args.overlap_chars,
            )
        )

    write_jsonl(args.output, records)
    print(f"Read {len(issues)} issues from {args.input}")
    print(f"Wrote {len(records)} chunks to {args.output}")


if __name__ == "__main__":
    main()
