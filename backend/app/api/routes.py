"""
HTTP routes — the API surface the frontend calls.

Why this file is thin:
- All logic lives in services/. Routes only: validate input, call services, format response.
- This makes routes easy to read and services easy to test in isolation.
"""

import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    SourceReference,
    HealthResponse,
    JurisdictionInfo,
    TitleRequest,
    TitleResponse,
)
from app.services import retrieval, llm
from app import config

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    """
    Liveness + readiness check.
    """
    try:
        count = retrieval.get_chunk_count()
        loaded = count > 0
    except Exception:
        count, loaded = 0, False

    return HealthResponse(
        status="ok",
        vector_store_loaded=loaded,
        chunk_count=count,
        llm_provider=config.LLM_BASE_URL,
    )


@router.get("/warmup")
def warmup():
    """
    Manually load the embedding model into memory.
    
    Why this exists:
    - Render's free tier spins down after 15 minutes.
    - The first query takes 30-60s to load PyTorch and the embedding model.
    - Hitting this endpoint 5 minutes before the demo wakes up the server and loads the model,
      so the first real user query is fast (2-5 seconds).
    """
    try:
        # Import here to avoid circular imports and only load when called
        from app.services.retrieval import _get_model
        _get_model()
        return {"status": "warm", "message": "Embedding model loaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Warmup failed: {str(e)}")


@router.get("/jurisdictions", response_model=list[JurisdictionInfo])
def jurisdictions():
    """
    Return all jurisdictions defined in config.
    """
    return [
        JurisdictionInfo(code=code, regulator=info["regulator"], name=info["name"])
        for code, info in config.JURISDICTIONS.items()
    ]


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Standard chat endpoint (blocking).
    Kept for completeness, though the frontend uses /chat/stream for the UI.
    """
    if req.jurisdiction not in config.JURISDICTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown jurisdiction: {req.jurisdiction}")

    chunks = retrieval.retrieve_chunks(req.question, req.jurisdiction)
    if not chunks:
        raise HTTPException(status_code=404, detail="No relevant content found in the document.")

    try:
        answer = llm.generate_answer(req.question, chunks)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM provider error: {str(e)}")

    sources = [
        SourceReference(
            page=c["page"],
            section=c["section"],
            document=c["document"],
        )
        for c in chunks
    ]

    return ChatResponse(
        answer=answer,
        sources=sources,
        session_id=req.session_id or str(uuid.uuid4()),
        model_used=config.LLM_MODEL,
    )


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).
    Why: Makes the UI feel instant by sending the text word-by-word.
    """
    if req.jurisdiction not in config.JURISDICTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown jurisdiction: {req.jurisdiction}")

    # 1. Retrieve the context
    chunks = retrieval.retrieve_chunks(req.question, req.jurisdiction)
    
    # 2. Return a streaming response that pipes text from Groq to the browser
    return StreamingResponse(
        llm.stream_answer(req.question, chunks),
        media_type="text/event-stream"
    )


@router.post("/title", response_model=TitleResponse)
def title(req: TitleRequest):
    """Generate a short conversation title."""
    title_text = llm.generate_title(req.question)
    return TitleResponse(title=title_text)