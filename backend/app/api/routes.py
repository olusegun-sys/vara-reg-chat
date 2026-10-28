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


@router.get("/debug-search")
def debug_search(q: str, jurisdiction: str = "AE-Dubai"):
    """
    Temporary endpoint to see exactly what chunks retrieval returns.
    Usage: /api/debug-search?q=What is the capital requirement?
    """
    try:
        chunks = retrieval.retrieve_chunks(q, jurisdiction)
        return {
            "query": q,
            "num_chunks_found": len(chunks),
            "chunks": [
                {
                    "page": c["page"],
                    "section": c["section"],
                    "document": c["document"],
                    "distance": c.get("distance", 0),
                    "text_snippet": c["text"][:150] + "..." 
                }
                for c in chunks
            ]
        }
    except Exception as e:
        return {"error": str(e), "query": q}