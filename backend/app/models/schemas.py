from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    jurisdiction: str = Field(default="AE-Dubai")
    session_id: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = Field(default_factory=list)


class SourceReference(BaseModel):
    page: int
    section: str
    document: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceReference]
    session_id: str
    model_used: str


class HealthResponse(BaseModel):
    status: str
    vector_store_loaded: bool
    chunk_count: int
    llm_provider: str


class JurisdictionInfo(BaseModel):
    code: str
    regulator: str
    name: str


class TitleRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


class TitleResponse(BaseModel):
    title: str