import argparse
import json
from pathlib import Path

import httpx

DEFAULT_OUTPUT = Path("data/raw/pandas_closed_issues.json")
REPO = "pandas-dev/pandas"
GITHUB_API = f"https://api.github.com/repos/{REPO}/issues"


def fetch_issues(limit: int) -> list[dict]:
    issues: list[dict] = []
    page = 1
    per_page = min(100, limit)

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "maintainers-copilot-local-script",
    }

    while len(issues) < limit:
        params = {
            "state": "closed",
            "per_page": per_page,
            "page": page,
            "sort": "updated",
            "direction": "desc",
        }

        response = httpx.get(
            GITHUB_API,
            headers=headers,
            params=params,
            timeout=30,
        )

        if response.status_code == 422:
            print(
                f"GitHub returned 422 on page {page}. "
                f"Stopping safely with {len(issues)} records."
            )
            break

        response.raise_for_status()

        batch = response.json()

        if not batch:
            break

        issues.extend(batch)
        print(f"Fetched page {page}: total records = {len(issues)}")

        page += 1

    return issues[:limit]


def write_json(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch closed pandas issues from GitHub.")
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    issues = fetch_issues(args.limit)
    write_json(args.output, issues)

    print(f"Saved {len(issues)} records to {args.output}")


if __name__ == "__main__":
    main()