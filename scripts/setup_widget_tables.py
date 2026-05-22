import json
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
                CREATE TABLE IF NOT EXISTS widget_configs (
                    widget_id TEXT PRIMARY KEY,
                    allowed_origins JSONB NOT NULL,
                    theme JSONB NOT NULL,
                    greeting TEXT NOT NULL,
                    enabled_tools JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

            cur.execute(
                """
                INSERT INTO widget_configs (
                    widget_id,
                    allowed_origins,
                    theme,
                    greeting,
                    enabled_tools
                )
                VALUES (
                    %(widget_id)s,
                    %(allowed_origins)s,
                    %(theme)s,
                    %(greeting)s,
                    %(enabled_tools)s
                )
                ON CONFLICT (widget_id) DO UPDATE SET
                    allowed_origins = EXCLUDED.allowed_origins,
                    theme = EXCLUDED.theme,
                    greeting = EXCLUDED.greeting,
                    enabled_tools = EXCLUDED.enabled_tools,
                    updated_at = now()
                """,
                {
                    "widget_id": "local-pandas",
                    "allowed_origins": json.dumps(
                        [
                            "http://localhost:5173",
                            "http://127.0.0.1:5173",
                            "http://localhost:8080",
                            "http://127.0.0.1:8080",
                        ]
                    ),
                    "theme": json.dumps(
                        {
                            "primary": "#0f766e",
                            "position": "bottom-right",
                        }
                    ),
                    "greeting": "Ask about pandas maintenance, docs, and resolved issues.",
                    "enabled_tools": json.dumps(
                        [
                            "rag",
                            "ner",
                            "summarizer",
                            "write_memory",
                        ]
                    ),
                },
            )

        conn.commit()

    print("Widget config table is ready.")
    print("Seeded widget config: local-pandas")


if __name__ == "__main__":
    main()