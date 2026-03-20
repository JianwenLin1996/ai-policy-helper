from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class IngestResponse(BaseModel):
    indexed_docs: int
    indexed_chunks: int

class AskRequest(BaseModel):
    query: str
    k: int | None = 4
    session_id: int

class Citation(BaseModel):
    title: str
    section: str | None = None

class Chunk(BaseModel):
    title: str
    section: str | None = None
    text: str

class AskResponse(BaseModel):
    query: str
    answer: str
    citations: List[Citation]
    chunks: List[Chunk]
    metrics: Dict[str, Any]

class MetricsResponse(BaseModel):
    total_docs: int
    total_chunks: int
    avg_retrieval_latency_ms: float
    avg_generation_latency_ms: float
    embedding_model: str
    llm_model: str

class SessionResponse(BaseModel):
    id: int
    created_at: datetime

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
