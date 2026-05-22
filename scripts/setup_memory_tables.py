import os

import psycopg

DEFAULT_DATABASE_URL = (
    "postgresql://maintainers:maintainers-local-password@localhost:5432/maintainers"
)


def main() -> None:
    database_url = os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS long_term_memories (
                    id BIGSERIAL PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    embedding vector(1536),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_long_term_memories_conversation_id
                ON long_term_memories (conversation_id)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_long_term_memories_embedding
                ON long_term_memories
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id BIGSERIAL PRIMARY KEY,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_logs_actor
                ON audit_logs (actor)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_logs_action
                ON audit_logs (action)
                """
            )

        conn.commit()

    print("Memory and audit tables are ready.")


if __name__ == "__main__":
    main()