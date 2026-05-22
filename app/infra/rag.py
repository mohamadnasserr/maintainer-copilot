import hashlib
import json
import os
import re
from typing import Any

import numpy as np
import psycopg

from app.domain.models import RetrievedChunk

DEFAULT_TOP_K = 5
EMBEDDING_DIM = 1536

# This default works when running Python locally from Windows.
# Inside Docker, use DATABASE_URL with host=db instead.
DEFAULT_DATABASE_URL = (
    "postgresql://maintainers:maintainers-local-password@localhost:5432/maintainers"
)

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_\.]*|\d+")


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def deterministic_dev_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """
    Local deterministic embedding used for development.

    Important:
    This must match the embedding method used in scripts/ingest_corpus.py
    when ingestion is run with --dev-embeddings.
    """
    vector = np.zeros(dim, dtype=np.float32)
    tokens = tokenize(text)

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector.tolist()


def embedding_to_pgvector(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def trim_text(text: str, limit: int = 900) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def issue_label(metadata: dict[str, Any]) -> str:
    issue_number = metadata.get("issue_number")
    if issue_number:
        return f"pandas issue #{issue_number}"
    return "pandas corpus"


def safe_tsquery(tokens: list[str]) -> str:
    """
    Build a safe PostgreSQL full-text query.

    Example:
        ["groupby", "value_counts", "performance"]
        -> "groupby | value_counts | performance"

    If tokens are empty, return a harmless fallback.
    """
    clean_tokens = []
    for token in tokens:
        token = re.sub(r"[^A-Za-z0-9_]", "", token)
        if token:
            clean_tokens.append(token)

    if not clean_tokens:
        return "pandas"

    return " | ".join(clean_tokens[:12])


def metadata_filter_sql(metadata_filter: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
    """
    Converts simple metadata filters into SQL WHERE clauses.

    Examples:
        {"kind": "closed_issue"}
        {"labels": ["Performance", "Groupby"]}

    For list values, it checks whether the JSONB array contains any requested value.
    """
    if not metadata_filter:
        return "", {}

    clauses: list[str] = []
    params: dict[str, Any] = {}

    for index, (key, expected) in enumerate(metadata_filter.items()):
        key_param = f"meta_key_{index}"
        value_param = f"meta_value_{index}"

        params[key_param] = key

        if isinstance(expected, list):
            item_params: list[str] = []

            for value_index, value in enumerate(expected):
                param_name = f"{value_param}_{value_index}"
                params[param_name] = str(value)
                item_params.append(f"%({param_name})s")

            clauses.append(
                f"""
                EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements_text(metadata -> %({key_param})s) AS item
                    WHERE item IN ({", ".join(item_params)})
                )
                """
            )
        else:
            params[value_param] = str(expected)
            clauses.append(f"metadata ->> %({key_param})s = %({value_param})s")

    return " AND " + " AND ".join(clauses), params


def exact_match_sql_and_params(tokens: list[str]) -> tuple[str, dict[str, Any]]:
    """
    Adds a bonus when exact technical terms appear in the title/body.

    This helps code-style terms like:
    - groupby
    - value_counts
    - read_csv
    - numeric_only
    - DataFrame
    """
    important_terms = [token for token in tokens if len(token) >= 4]

    conditions: list[str] = []
    params: dict[str, Any] = {}

    for index, token in enumerate(important_terms[:8]):
        param_name = f"exact_term_{index}"
        params[param_name] = f"%{token.lower()}%"
        conditions.append(
            f"""
            CASE
                WHEN lower(coalesce(title, '') || ' ' || coalesce(body, ''))
                     LIKE %({param_name})s
                THEN 1.0
                ELSE 0.0
            END
            """
        )

    if not conditions:
        return "0.0", {}

    return " + ".join(conditions), params


class RagPipeline:
    def __init__(
        self,
        database_url: str | None = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> None:
        self.database_url = (
            database_url
            or os.getenv("DATABASE_URL")
            or DEFAULT_DATABASE_URL
        )
        self.top_k = top_k

    def retrieve(
        self,
        question: str,
        top_k: int = DEFAULT_TOP_K,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        question = question.strip()
        if not question:
            return []

        query_tokens = tokenize(question)
        keyword_query = safe_tsquery(query_tokens)

        query_embedding = deterministic_dev_embedding(question)
        query_vector = embedding_to_pgvector(query_embedding)

        extra_where, filter_params = metadata_filter_sql(metadata_filter)
        exact_match_sql, exact_match_params = exact_match_sql_and_params(query_tokens)

        sql = f"""
            SELECT
                id,
                repo,
                source_url,
                title,
                body,
                metadata,
                1 - (embedding <=> %(query_vector)s::vector) AS vector_similarity,
                ts_rank_cd(
                    to_tsvector(
                        'english',
                        coalesce(title, '') || ' ' || coalesce(body, '')
                    ),
                    to_tsquery('english', %(keyword_query)s)
                ) AS keyword_score,
                ({exact_match_sql}) AS exact_match_score
            FROM document_chunks
            WHERE embedding IS NOT NULL
            {extra_where}
            ORDER BY
                (
                    0.55 * (1 - (embedding <=> %(query_vector)s::vector))
                    +
                    0.25 * ts_rank_cd(
                        to_tsvector(
                            'english',
                            coalesce(title, '') || ' ' || coalesce(body, '')
                        ),
                        to_tsquery('english', %(keyword_query)s)
                    )
                    +
                    0.20 * ({exact_match_sql})
                ) DESC
            LIMIT %(top_k)s
        """

        params: dict[str, Any] = {
            "query_vector": query_vector,
            "keyword_query": keyword_query,
            "top_k": top_k,
            **filter_params,
            **exact_match_params,
        }

        results: list[RetrievedChunk] = []

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

        for row in rows:
            (
                chunk_id,
                repo,
                source_url,
                title,
                body,
                metadata,
                vector_similarity,
                keyword_score,
                exact_match_score,
            ) = row

            if isinstance(metadata, str):
                metadata_dict = json.loads(metadata)
            else:
                metadata_dict = dict(metadata or {})

            combined_score = (
                0.55 * float(vector_similarity or 0.0)
                + 0.25 * float(keyword_score or 0.0)
                + 0.20 * float(exact_match_score or 0.0)
            )
            score = round(combined_score, 6)

            results.append(
                RetrievedChunk(
                    chunk_id=str(chunk_id),
                    source_url=str(source_url or ""),
                    title=str(title or "Untitled pandas chunk"),
                    text=str(body or ""),
                    score=score,
                    metadata={
                        **metadata_dict,
                        "repo": repo,
                        "retrieval": {
                            "strategy": "postgres_pgvector_plus_keyword_plus_exact_match",
                            "vector_similarity": round(float(vector_similarity or 0.0), 6),
                            "keyword_score": round(float(keyword_score or 0.0), 6),
                            "exact_match_score": round(float(exact_match_score or 0.0), 6),
                            "combined_score": score,
                        },
                    },
                )
            )

        return results

    def answer(self, question: str) -> tuple[str, list[RetrievedChunk]]:
        chunks = self.retrieve(question, top_k=self.top_k)

        if not chunks:
            answer = (
                "I could not find matching pandas maintainer context in the database. "
                "Make sure the pandas chunks were ingested into Postgres using "
                "`scripts/ingest_corpus.py`."
            )
            return answer, []

        lines = [
            "Based on the pandas issue corpus stored in Postgres/pgvector, "
            "the most relevant maintainer context is:"
        ]

        for index, chunk in enumerate(chunks[:3], start=1):
            lines.append(
                f"{index}. {issue_label(chunk.metadata)}: {chunk.title}. "
                f"{trim_text(chunk.text)}"
            )

        lines.append(
            "Use the source URLs and issue metadata to inspect the original pandas issues "
            "before making a maintainer decision."
        )

        return "\n".join(lines), chunks