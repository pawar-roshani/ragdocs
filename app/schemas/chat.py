import uuid

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    document_id: uuid.UUID | None = Field(
        default=None,
        description="Optional: restrict retrieval to a single document.",
    )
    top_k: int | None = Field(default=None, ge=1, le=20)


class SourceChunk(BaseModel):
    document_id: uuid.UUID
    filename: str
    chunk_index: int
    content: str
    similarity: float


class AskResponse(BaseModel):
    answer: str
    generation_mode: str  # "openai" | "extractive"
    sources: list[SourceChunk]
