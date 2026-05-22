import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import psycopg
from openai import OpenAI

DEFAULT_INPUT = Path("data/processed/pandas_chunks.jsonl")
DEFAULT_DATABASE_URL = "postgresql://app:app@localhost:5432/app"
EMBEDDING_DIM = 1536
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run `python scripts/build_pandas_chunks.py` first."
        )

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc

            records.append(record)

    return records


def normalize_text(record: dict[str, Any]) -> str:
    title = str(record.get("title") or "").strip()
    body = str(record.get("body") or record.get("text") or "").strip()

    if title and body:
        return f"{title}\n\n{body}"
    return title or body


def deterministic_dev_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """
    Development fallback only.

    This lets the pipeline run even without an OpenAI API key.
    It is not a high-quality semantic embedding model.
    For the final project, use OpenAI or another real embedding model.
    """
    vector = np.zeros(dim, dtype=np.float32)
    tokens = text.lower().split()

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector.tolist()


def openai_embedding(client: OpenAI, text: str) -> list[float]:
    response = client.embeddings.create(
        model=OPENAI_EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def embedding_to_pgvector(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def ensure_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS document_chunks (
                id TEXT PRIMARY KEY,
                repo TEXT NOT NULL,
                source_url TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                metadata JSONB NOT NULL,
                embedding vector(1536)
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
            ON document_chunks
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_document_chunks_metadata
            ON document_chunks
            USING gin (metadata)
            """
        )
    conn.commit()


def upsert_chunk(
    conn: psycopg.Connection,
    record: dict[str, Any],
    embedding: list[float],
) -> None:
    chunk_id = str(record["id"])
    repo = str(record.get("repo") or "pandas-dev/pandas")
    source_url = str(record.get("source_url") or "")
    title = str(record.get("title") or "")
    body = str(record.get("body") or record.get("text") or "")
    metadata = record.get("metadata") or {}

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO document_chunks (
                id,
                repo,
                source_url,
                title,
                body,
                metadata,
                embedding
            )
            VALUES (
                %(id)s,
                %(repo)s,
                %(source_url)s,
                %(title)s,
                %(body)s,
                %(metadata)s,
                %(embedding)s::vector
            )
            ON CONFLICT (id) DO UPDATE SET
                repo = EXCLUDED.repo,
                source_url = EXCLUDED.source_url,
                title = EXCLUDED.title,
                body = EXCLUDED.body,
                metadata = EXCLUDED.metadata,
                embedding = EXCLUDED.embedding
            """,
            {
                "id": chunk_id,
                "repo": repo,
                "source_url": source_url,
                "title": title,
                "body": body,
                "metadata": json.dumps(metadata),
                "embedding": embedding_to_pgvector(embedding),
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Embed pandas chunks and store them in Postgres pgvector."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
    )
    parser.add_argument(
        "--dev-embeddings",
        action="store_true",
        help="Use deterministic local embeddings instead of OpenAI. Good for local testing only.",
    )
    args = parser.parse_args()

    records = load_jsonl(args.input)

    if not records:
        raise ValueError(f"No records found in {args.input}")

    use_openai = not args.dev_embeddings
    client: OpenAI | None = None

    if use_openai:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is missing. Either set it or run with --dev-embeddings."
            )
        client = OpenAI()

    print(f"Loaded {len(records)} chunks from {args.input}")

    with psycopg.connect(args.database_url) as conn:
        ensure_schema(conn)

        for index, record in enumerate(records, start=1):
            text = normalize_text(record)

            if not text:
                print(f"Skipping empty record: {record.get('id')}")
                continue

            if client is not None:
                embedding = openai_embedding(client, text)
            else:
                embedding = deterministic_dev_embedding(text)

            upsert_chunk(conn, record, embedding)

            if index % 25 == 0:
                conn.commit()
                print(f"Ingested {index}/{len(records)} chunks")

        conn.commit()

    print(f"Done. Ingested {len(records)} chunks into document_chunks.")


if __name__ == "__main__":
    main()