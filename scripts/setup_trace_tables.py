import os

import psycopg

DEFAULT_DATABASE_URL = (
    "postgresql://maintainers:maintainers-local-password@localhost:5432/maintainers"
)


def main() -> None:
    database_url = os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS trace_spans (
                    id BIGSERIAL PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    request_id TEXT,
                    conversation_id TEXT,
                    parent_span_id BIGINT,
                    span_name TEXT NOT NULL,
                    span_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ok',
                    input_preview TEXT,
                    output_preview TEXT,
                    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
                    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    ended_at TIMESTAMPTZ,
                    duration_ms DOUBLE PRECISION
                )
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_trace_spans_trace_id
                ON trace_spans (trace_id)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_trace_spans_conversation_id
                ON trace_spans (conversation_id)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_trace_spans_span_type
                ON trace_spans (span_type)
                """
            )

        conn.commit()

    print("Trace span table is ready.")


if __name__ == "__main__":
    main()

