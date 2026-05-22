from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.nlp_tools import extract_entities, summarize_text

router = APIRouter(prefix="/nlp", tags=["nlp"])


class TextRequest(BaseModel):
    text: str = Field(..., min_length=1)


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    max_sentences: int = Field(default=3, ge=1, le=10)


@router.post("/entities")
def entities(request: TextRequest) -> dict[str, Any]:
    return extract_entities(request.text)


@router.post("/summarize")
def summarize(request: SummarizeRequest) -> dict[str, Any]:
    return summarize_text(
        request.text,
        max_sentences=request.max_sentences,
    )