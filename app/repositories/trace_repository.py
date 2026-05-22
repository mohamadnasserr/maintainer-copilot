import json
import os
from time import perf_counter
from typing import Any

import psycopg

from app.infra.redaction import redact_for_log

DEFAULT_DATABASE_URL = (
    "postgresql://maintainers:maintainers-local-password@localhost:5432/maintainers"
)


class TraceRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = (
            database_url
            or os.getenv("DATABASE_URL")
            or DEFAULT_DATABASE_URL
        )

    def start_span(
        self,
        trace_id: str,
        span_name: str,
        span_type: str,
        request_id: str | None = None,
        conversation_id: str | None = None,
        parent_span_id: int | None = None,
        input_preview: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> tuple[int, float]:
        safe_input = redact_for_log(input_preview or "")
        safe_attributes = json.dumps(attributes or {}, ensure_ascii=False)

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trace_spans (
                        trace_id,
                        request_id,
                        conversation_id,
                        parent_span_id,
                        span_name,
                        span_type,
                        input_preview,
                        attributes
                    )
                    VALUES (
                        %(trace_id)s,
                        %(request_id)s,
                        %(conversation_id)s,
                        %(parent_span_id)s,
                        %(span_name)s,
                        %(span_type)s,
                        %(input_preview)s,
                        %(attributes)s
                    )
                    RETURNING id
                    """,
                    {
                        "trace_id": trace_id,
                        "request_id": request_id,
                        "conversation_id": conversation_id,
                        "parent_span_id": parent_span_id,
                        "span_name": span_name,
                        "span_type": span_type,
                        "input_preview": safe_input[:500],
                        "attributes": safe_attributes,
                    },
                )
                span_id = cur.fetchone()[0]

            conn.commit()

        return int(span_id), perf_counter()

    def finish_span(
        self,
        span_id: int,
        started_perf_counter: float,
        status: str = "ok",
        output_preview: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        duration_ms = round((perf_counter() - started_perf_counter) * 1000, 2)
        safe_output = redact_for_log(output_preview or "")
        safe_attributes = json.dumps(attributes or {}, ensure_ascii=False)

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE trace_spans
                    SET
                        status = %(status)s,
                        output_preview = %(output_preview)s,
                        attributes = attributes || %(attributes)s::jsonb,
                        ended_at = now(),
                        duration_ms = %(duration_ms)s
                    WHERE id = %(span_id)s
                    """,
                    {
                        "span_id": span_id,
                        "status": status,
                        "output_preview": safe_output[:500],
                        "attributes": safe_attributes,
                        "duration_ms": duration_ms,
                    },
                )

            conn.commit()

    def list_spans(
        self,
        trace_id: str | None = None,
        conversation_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        where_clauses = []
        params: dict[str, Any] = {"limit": limit}

        if trace_id:
            where_clauses.append("trace_id = %(trace_id)s")
            params["trace_id"] = trace_id

        if conversation_id:
            where_clauses.append("conversation_id = %(conversation_id)s")
            params["conversation_id"] = conversation_id

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        id,
                        trace_id,
                        request_id,
                        conversation_id,
                        parent_span_id,
                        span_name,
                        span_type,
                        status,
                        input_preview,
                        output_preview,
                        attributes,
                        started_at,
                        ended_at,
                        duration_ms
                    FROM trace_spans
                    {where_sql}
                    ORDER BY started_at DESC
                    LIMIT %(limit)s
                    """,
                    params,
                )
                rows = cur.fetchall()

        spans: list[dict[str, Any]] = []

        for row in rows:
            (
                span_id,
                trace_id_value,
                request_id,
                conversation_id_value,
                parent_span_id,
                span_name,
                span_type,
                status,
                input_preview,
                output_preview,
                attributes,
                started_at,
                ended_at,
                duration_ms,
            ) = row

            spans.append(
                {
                    "id": span_id,
                    "trace_id": trace_id_value,
                    "request_id": request_id,
                    "conversation_id": conversation_id_value,
                    "parent_span_id": parent_span_id,
                    "span_name": span_name,
                    "span_type": span_type,
                    "status": status,
                    "input_preview": input_preview,
                    "output_preview": output_preview,
                    "attributes": attributes,
                    "started_at": started_at.isoformat() if started_at else None,
                    "ended_at": ended_at.isoformat() if ended_at else None,
                    "duration_ms": duration_ms,
                }
            )

        return spans