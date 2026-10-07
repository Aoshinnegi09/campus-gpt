from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks_created: int


class DocumentItem(BaseModel):
    document_id: str
    filename: str
    chunk_count: int


class Citation(BaseModel):
    document_id: str
    filename: str
    chunk_id: str
    score: float
    snippet: str


class ChatRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=10)


class RetrievalMetadata(BaseModel):
    max_score: float
    threshold: float
    top_k: int


class ChatResponse(BaseModel):
    grounded: bool
    refused: bool
    answer: str
    confidence: float
    citations: list[Citation]
    retrieval: RetrievalMetadata
