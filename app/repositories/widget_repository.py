import json
import os
from typing import Any

import psycopg

DEFAULT_DATABASE_URL = (
    "postgresql://maintainers:maintainers-local-password@localhost:5432/maintainers"
)


class WidgetRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = (
            database_url
            or os.getenv("DATABASE_URL")
            or DEFAULT_DATABASE_URL
        )

    def get_config(self, widget_id: str) -> dict[str, Any] | None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        widget_id,
                        allowed_origins,
                        theme,
                        greeting,
                        enabled_tools
                    FROM widget_configs
                    WHERE widget_id = %(widget_id)s
                    """,
                    {
                        "widget_id": widget_id,
                    },
                )

                row = cur.fetchone()

        if row is None:
            return None

        widget_id, allowed_origins, theme, greeting, enabled_tools = row

        return {
            "widget_id": widget_id,
            "allowed_origins": allowed_origins,
            "theme": theme,
            "greeting": greeting,
            "enabled_tools": enabled_tools,
        }

    def upsert_config(
        self,
        widget_id: str,
        allowed_origins: list[str],
        theme: dict[str, Any],
        greeting: str,
        enabled_tools: list[str],
    ) -> dict[str, Any]:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
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
                    RETURNING
                        widget_id,
                        allowed_origins,
                        theme,
                        greeting,
                        enabled_tools
                    """,
                    {
                        "widget_id": widget_id,
                        "allowed_origins": json.dumps(allowed_origins),
                        "theme": json.dumps(theme),
                        "greeting": greeting,
                        "enabled_tools": json.dumps(enabled_tools),
                    },
                )

                row = cur.fetchone()

            conn.commit()

        returned_widget_id, returned_allowed_origins, returned_theme, returned_greeting, returned_enabled_tools = row

        return {
            "widget_id": returned_widget_id,
            "allowed_origins": returned_allowed_origins,
            "theme": returned_theme,
            "greeting": returned_greeting,
            "enabled_tools": returned_enabled_tools,
        }