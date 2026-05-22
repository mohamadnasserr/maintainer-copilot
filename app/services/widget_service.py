from typing import Any

from app.repositories.widget_repository import WidgetRepository


class WidgetService:
    def __init__(self) -> None:
        self.repository = WidgetRepository()

    def get_config(self, widget_id: str) -> dict[str, Any]:
        config = self.repository.get_config(widget_id)

        if config is not None:
            return config

        return {
            "widget_id": widget_id,
            "allowed_origins": [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ],
            "theme": {
                "primary": "#0f766e",
                "position": "bottom-right",
            },
            "greeting": "Ask about pandas maintenance.",
            "enabled_tools": [
                "rag",
                "ner",
                "summarizer",
                "write_memory",
            ],
        }

    def upsert_config(
        self,
        widget_id: str,
        allowed_origins: list[str],
        theme: dict[str, Any],
        greeting: str,
        enabled_tools: list[str],
    ) -> dict[str, Any]:
        return self.repository.upsert_config(
            widget_id=widget_id,
            allowed_origins=allowed_origins,
            theme=theme,
            greeting=greeting,
            enabled_tools=enabled_tools,
        )


widget_service = WidgetService()