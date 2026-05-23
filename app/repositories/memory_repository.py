from importlib.metadata import metadata
import json
import os
from typing import Any
from app.infra.redaction import redact_for_log
import psycopg

DEFAULT_DATABASE_URL = (
    "postgresql://maintainers:maintainers-local-password@localhost:5432/maintainers"
)


class MemoryRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = (
            database_url
            or os.getenv("DATABASE_URL")
            or DEFAULT_DATABASE_URL
        )

    def write_memory(
        self,
        conversation_id: str,
        actor: str,
        memory_type: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        embedding: str | None = None,
    ) -> int:
        metadata = metadata or {}
        safe_content = redact_for_log(content)
        safe_metadata = redact_for_log(metadata or {})

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO long_term_memories (
                        conversation_id,
                        actor,
                        memory_type,
                        content,
                        metadata,
                        embedding
                    )
                    VALUES (
                        %(conversation_id)s,
                        %(actor)s,
                        %(memory_type)s,
                        %(content)s,
                        %(metadata)s,
                        %(embedding)s::vector
                    )
                    RETURNING id
                    """,
                    {
                        "conversation_id": conversation_id,
                        "actor": actor,
                        "memory_type": memory_type,
                        "content": safe_content,
                        "metadata": json.dumps(safe_metadata),
                        "embedding": embedding,
                    },
                )

                memory_id = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO audit_logs (
                        actor,
                        action,
                        target,
                        metadata
                    )
                    VALUES (
                        %(actor)s,
                        %(action)s,
                        %(target)s,
                        %(metadata)s
                    )
                    """,
                    {
                        "actor": actor,
                        "action": "write_memory",
                        "target": f"long_term_memories:{memory_id}",
                        "metadata": json.dumps(
                            {
                                "conversation_id": conversation_id,
                                "memory_type": memory_type,
                            }
                        ),
                    },
                )

            conn.commit()

        return int(memory_id)

    def list_memories(
        self,
        conversation_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        conversation_id,
                        actor,
                        memory_type,
                        content,
                        metadata,
                        created_at
                    FROM long_term_memories
                    WHERE conversation_id = %(conversation_id)s
                    ORDER BY created_at DESC
                    LIMIT %(limit)s
                    """,
                    {
                        "conversation_id": conversation_id,
                        "limit": limit,
                    },
                )

                rows = cur.fetchall()

        memories: list[dict[str, Any]] = []

        for row in rows:
            memory_id, conv_id, actor, memory_type, content, metadata, created_at = row

            memories.append(
                {
                    "id": memory_id,
                    "conversation_id": conv_id,
                    "actor": actor,
                    "memory_type": memory_type,
                    "content": content,
                    "metadata": metadata,
                    "created_at": created_at.isoformat(),
                }
            )

        return memories

    def count_audit_logs(self) -> int:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM audit_logs")
                count = cur.fetchone()[0]

        return int(count)