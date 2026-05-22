import json
from pathlib import Path

seen = set()
rows = []

path = Path("data/processed/pandas_chunks.jsonl")

for line in path.read_text(encoding="utf-8").splitlines():
    obj = json.loads(line)
    metadata = obj.get("metadata", {})
    issue_number = metadata.get("issue_number")
    title = obj.get("title", "")
    labels = metadata.get("labels", [])
    text = (obj.get("text") or obj.get("body") or "")[:220].replace("\n", " ")

    if issue_number and issue_number not in seen:
        seen.add(issue_number)
        rows.append((issue_number, title, labels, text))

for index, (issue_number, title, labels, text) in enumerate(rows[:35], start=1):
    print(f"{index}. #{issue_number} | {title} | labels={labels} | text={text}")