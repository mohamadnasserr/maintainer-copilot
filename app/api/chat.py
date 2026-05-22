from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: str | None = None
    widget_id: str | None = None


class Source(BaseModel):
    chunk_id: str
    title: str
    source_url: str
    score: float
    metadata: dict[str, Any]


class MemoryMessage(BaseModel):
    role: str
    content: str
    metadata: dict[str, Any]
    timestamp: int

class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[Source]
    memory: list[MemoryMessage]
    long_term_memory_written: bool = False
    long_term_memory_id: int | None = None
    tool_used: str = "rag"

@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    conversation_id = request.conversation_id or request.widget_id
    result = chat_service.answer(
        message=request.message,
        conversation_id=conversation_id,
    )
    return ChatResponse(**result)

@router.get("/memory/{conversation_id}")
def get_memory(conversation_id: str) -> dict[str, Any]:
    memories = chat_service.long_term_memory.list_memories(
        conversation_id=conversation_id,
        limit=20,
    )
    audit_count = chat_service.long_term_memory.count_audit_logs()

    return {
        "conversation_id": conversation_id,
        "memories": memories,
        "audit_count": audit_count,
    }