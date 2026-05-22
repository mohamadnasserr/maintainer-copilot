import json
import os
import time
from typing import Any

import redis

DEFAULT_REDIS_URL = "redis://localhost:6379/0"
DEFAULT_TTL_SECONDS = 60 * 60  # 1 hour


class RedisShortTermMemory:
    def __init__(
        self,
        redis_url: str | None = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self.redis_url = redis_url or os.getenv("REDIS_URL") or DEFAULT_REDIS_URL
        self.ttl_seconds = ttl_seconds
        self.client = redis.Redis.from_url(
            self.redis_url,
            decode_responses=True,
        )

    def _key(self, conversation_id: str) -> str:
        return f"conversation:{conversation_id}:messages"

    def append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": int(time.time()),
        }

        key = self._key(conversation_id)

        self.client.rpush(key, json.dumps(record, ensure_ascii=False))
        self.client.expire(key, self.ttl_seconds)

    def get_messages(
        self,
        conversation_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        key = self._key(conversation_id)

        raw_messages = self.client.lrange(key, -limit, -1)

        messages: list[dict[str, Any]] = []

        for raw_message in raw_messages:
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                continue

            if isinstance(message, dict):
                messages.append(message)

        return messages

    def clear(self, conversation_id: str) -> None:
        self.client.delete(self._key(conversation_id))