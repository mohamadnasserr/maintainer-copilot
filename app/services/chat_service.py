from typing import Any
from uuid import uuid4

from app.infra.rag import RagPipeline
from app.infra.redis_memory import RedisShortTermMemory
from app.repositories.memory_repository import MemoryRepository
from app.repositories.trace_repository import TraceRepository
from app.services.nlp_tools import extract_entities, summarize_text


MEMORY_PREFIXES = (
    "remember that ",
    "remember this: ",
    "save this: ",
    "store this: ",
)

ENTITY_PREFIXES = (
    "extract entities from:",
    "extract entities:",
    "find entities in:",
)

SUMMARY_PREFIXES = (
    "summarize this:",
    "summarize:",
    "summary of:",
)


class ChatService:
    def __init__(self) -> None:
        self.rag = RagPipeline()
        self.short_term_memory = RedisShortTermMemory()
        self.long_term_memory = MemoryRepository()
        self.traces = TraceRepository()

    def _extract_prefixed_content(
        self,
        message: str,
        prefixes: tuple[str, ...],
    ) -> str | None:
        stripped = message.strip()
        lowered = stripped.lower()

        for prefix in prefixes:
            if lowered.startswith(prefix):
                return stripped[len(prefix):].strip()

        return None

    def _format_entities_answer(self, text: str) -> str:
        result = extract_entities(text)
        entities = result.get("entities", [])

        if not entities:
            return "I did not find code-shaped entities in the provided text."

        lines = [
            f"Found {result.get('entity_count', len(entities))} code-shaped entities:"
        ]

        for entity in entities:
            lines.append(f"- `{entity['value']}` ({entity['type']})")

        return "\n".join(lines)

    def _format_summary_answer(self, text: str) -> str:
        result = summarize_text(text, max_sentences=3)
        summary = result.get("summary", "")

        if not summary:
            return "I could not summarize the provided text."

        return (
            "Summary:\n"
            f"{summary}\n\n"
            f"Strategy: `{result.get('strategy')}`"
        )

    def _finish_root_span(
        self,
        span_id: int,
        started: float,
        answer: str,
        tool_used: str,
    ) -> None:
        self.traces.finish_span(
            span_id=span_id,
            started_perf_counter=started,
            status="ok",
            output_preview=answer,
            attributes={
                "tool_used": tool_used,
            },
        )

    def answer(
        self,
        message: str,
        conversation_id: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        active_conversation_id = conversation_id or str(uuid4())
        active_trace_id = trace_id or str(uuid4())

        root_span_id, root_started = self.traces.start_span(
            trace_id=active_trace_id,
            request_id=request_id,
            conversation_id=active_conversation_id,
            span_name="chat_request",
            span_type="chat",
            input_preview=message,
            attributes={
                "conversation_id": active_conversation_id,
            },
        )

        self.short_term_memory.append_message(
            conversation_id=active_conversation_id,
            role="user",
            content=message,
        )

        memory_content = self._extract_prefixed_content(message, MEMORY_PREFIXES)

        if memory_content:
            memory_id = self.long_term_memory.write_memory(
                conversation_id=active_conversation_id,
                actor="user",
                memory_type="semantic",
                content=memory_content,
                metadata={
                    "source": "explicit_chat_request",
                },
            )

            answer = (
                f"Saved this to long-term memory as semantic memory #{memory_id}: "
                f"{memory_content}"
            )

            self.short_term_memory.append_message(
                conversation_id=active_conversation_id,
                role="assistant",
                content=answer,
                metadata={
                    "memory_id": memory_id,
                    "action": "write_memory",
                    "tool": "memory",
                },
            )

            recent_memory = self.short_term_memory.get_messages(
                conversation_id=active_conversation_id,
                limit=10,
            )

            self._finish_root_span(
                root_span_id,
                root_started,
                answer,
                "write_memory",
            )

            return {
                "conversation_id": active_conversation_id,
                "trace_id": active_trace_id,
                "answer": answer,
                "sources": [],
                "memory": recent_memory,
                "long_term_memory_written": True,
                "long_term_memory_id": memory_id,
                "tool_used": "write_memory",
            }

        entity_text = self._extract_prefixed_content(message, ENTITY_PREFIXES)

        if entity_text:
            answer = self._format_entities_answer(entity_text)

            self.short_term_memory.append_message(
                conversation_id=active_conversation_id,
                role="assistant",
                content=answer,
                metadata={
                    "tool": "ner",
                },
            )

            recent_memory = self.short_term_memory.get_messages(
                conversation_id=active_conversation_id,
                limit=10,
            )

            self._finish_root_span(
                root_span_id,
                root_started,
                answer,
                "ner",
            )

            return {
                "conversation_id": active_conversation_id,
                "trace_id": active_trace_id,
                "answer": answer,
                "sources": [],
                "memory": recent_memory,
                "long_term_memory_written": False,
                "long_term_memory_id": None,
                "tool_used": "ner",
            }

        summary_text = self._extract_prefixed_content(message, SUMMARY_PREFIXES)

        if summary_text:
            answer = self._format_summary_answer(summary_text)

            self.short_term_memory.append_message(
                conversation_id=active_conversation_id,
                role="assistant",
                content=answer,
                metadata={
                    "tool": "summarizer",
                },
            )

            recent_memory = self.short_term_memory.get_messages(
                conversation_id=active_conversation_id,
                limit=10,
            )

            self._finish_root_span(
                root_span_id,
                root_started,
                answer,
                "summarizer",
            )

            return {
                "conversation_id": active_conversation_id,
                "trace_id": active_trace_id,
                "answer": answer,
                "sources": [],
                "memory": recent_memory,
                "long_term_memory_written": False,
                "long_term_memory_id": None,
                "tool_used": "summarizer",
            }

        answer, chunks = self.rag.answer(message)

        self.short_term_memory.append_message(
            conversation_id=active_conversation_id,
            role="assistant",
            content=answer,
            metadata={
                "source_count": len(chunks),
                "tool": "rag",
            },
        )

        recent_memory = self.short_term_memory.get_messages(
            conversation_id=active_conversation_id,
            limit=10,
        )

        self._finish_root_span(
            root_span_id,
            root_started,
            answer,
            "rag",
        )

        return {
            "conversation_id": active_conversation_id,
            "trace_id": active_trace_id,
            "answer": answer,
            "sources": [
                {
                    "chunk_id": chunk.chunk_id,
                    "title": chunk.title,
                    "source_url": chunk.source_url,
                    "score": chunk.score,
                    "metadata": chunk.metadata,
                }
                for chunk in chunks
            ],
            "memory": recent_memory,
            "long_term_memory_written": False,
            "long_term_memory_id": None,
            "tool_used": "rag",
        }


chat_service = ChatService()