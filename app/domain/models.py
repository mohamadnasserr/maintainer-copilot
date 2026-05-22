from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str
    created_at: datetime


class RetrievedChunk(BaseModel):
    chunk_id: str
    source_url: str
    title: str
    text: str
    score: float
    metadata: dict[str, Any] = {}


class WidgetConfig(BaseModel):
    widget_id: str
    allowed_origins: list[str]
    theme: dict[str, str]
    greeting: str
    enabled_tools: list[str]

