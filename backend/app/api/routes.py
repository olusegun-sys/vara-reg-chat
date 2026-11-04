import uuid
import re
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    SourceReference,
    HealthResponse,
    JurisdictionInfo,
    TitleRequest,
    TitleResponse,
)
from app.services import retrieval, llm, memory, web_search
from app import config

router = APIRouter()


# --- Out-of-scope jurisdiction helper ---------------------------------------
# Why: the old code inlined this regex in 3 places. Centralising it means:
#   1. Adding a new jurisdiction (e.g. "baFin", "cma") is a one-line edit.
#   2. The pattern is \b-anchored so "us" doesn't match inside "custody".
#   3. It's obvious this is a "shortcut for known other regulators", not the
#      primary web-fallback mechanism. The primary mechanism is now the
#      confidence check (retrieval.is_low_confidence).
_OUT_OF_SCOPE_PATTERN = re.compile(
    r"\b(fca|sec|mas|finma|cbn|uk|us|usa|singapore|nigeria|bafin|cma|asic)\b",
    re.IGNORECASE,
)


def _needs_web_fallback(question: str, chunks: list) -> tuple:
    """
    Return (should_fallback: bool, reason: str).
    Two independent reasons to hit the web:
      A. The question explicitly names another regulator (FCA/SEC/etc.).
      B. FAISS returned low-confidence chunks (question doesn't really match the corpus).
    Either is sufficient. Both produce a helpful log line so we can debug.
    """
    if _OUT_OF_SCOPE_PATTERN.search(question):
        return True, "out-of-scope jurisdiction mentioned"
    if retrieval.is_low_confidence(chunks):
        best = min((c.get("distance", 99) for c in chunks), default=99)
        return True, f"low retrieval confidence (best distance={best:.3f})"
    return False, ""


# --- Session facts memory endpoint -----------------------------------------
class SaveFactsRequest(BaseModel):
    session_id: str
    user_message: str


@router.post("/memory/facts")
def extract_and_return_facts(req: SaveFactsRequest):
    try:
        facts = memory.extract_facts(req.user_message)
        return {"facts_saved": len(facts), "facts": facts}
    except Exception as e:
        return {"facts_saved": 0, "facts": [], "error": str(e)}


# --- Existing endpoints (unchanged) ----------------------------------------

@router.get("/health", response_model=HealthResponse)
def health():
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
    try:
        from app.services.retrieval import _get_model
        _get_model()
        return {"status": "warm", "message": "Embedding model loaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Warmup failed: {str(e)}")


@router.get("/jurisdictions", response_model=list[JurisdictionInfo])
def jurisdictions():
    return [
        JurisdictionInfo(code=code, regulator=info["regulator"], name=info["name"])
        for code, info in config.JURISDICTIONS.items()
    ]


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if req.jurisdiction not in config.JURISDICTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown jurisdiction: {req.jurisdiction}")

    search_query = llm.rewrite_query(req.question, req.jurisdiction)
    if not search_query.strip():
        search_query = req.question

    # Retrieve from internal corpus first.
    chunks = retrieval.retrieve_chunks(search_query, req.jurisdiction)

    # Ask the helper whether we should escalate to web search.
    should_fallback, reason = _needs_web_fallback(req.question, chunks)
    if should_fallback:
        print(f"[fallback] {reason}. Triggering web search.")
        web_chunks = web_search.search_web(req.question)
        # Prefer web results if we got any — they're more likely to be relevant
        # than a low-confidence FAISS hit. If web returned nothing, keep the
        # internal chunks so the answer is still grounded in something.
        if web_chunks:
            chunks = web_chunks

    if not chunks:
        raise HTTPException(status_code=404, detail="No relevant content found in the documents or the web.")

    try:
        answer = llm.generate_answer(req.question, chunks, req.history, req.jurisdiction)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM provider error: {str(e)}")

    sources = [
        SourceReference(
            page=c["page"],
            section=c["section"],
            document=c["document"],
            source_url=c.get("source_url", ""),
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
    if req.jurisdiction not in config.JURISDICTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown jurisdiction: {req.jurisdiction}")

    search_query = llm.rewrite_query(req.question, req.jurisdiction)
    if not search_query.strip():
        search_query = req.question

    chunks = retrieval.retrieve_chunks(search_query, req.jurisdiction)

    should_fallback, reason = _needs_web_fallback(req.question, chunks)
    if should_fallback:
        print(f"[fallback] {reason}. Triggering web search.")
        web_chunks = web_search.search_web(req.question)
        if web_chunks:
            chunks = web_chunks

    return StreamingResponse(
        llm.stream_answer(req.question, chunks, req.history, req.jurisdiction),
        media_type="text/event-stream"
    )


@router.post("/title", response_model=TitleResponse)
def title(req: TitleRequest):
    title_text = llm.generate_title(req.question)
    return TitleResponse(title=title_text)


@router.get("/debug-search")
def debug_search(q: str, jurisdiction: str = "AE-Dubai"):
    try:
        search_query = llm.rewrite_query(q, jurisdiction)
        if not search_query.strip():
            search_query = q

        chunks = retrieval.retrieve_chunks(search_query, jurisdiction)

        should_fallback, reason = _needs_web_fallback(q, chunks)
        internal_chunks = chunks  # preserve for the debug payload
        if should_fallback:
            print(f"[debug-search fallback] {reason}. Triggering web search.")
            web_chunks = web_search.search_web(q)
            if web_chunks:
                chunks = web_chunks

        best_dist = min((c.get("distance", 99) for c in internal_chunks), default=None)

        return {
            "original_query": q,
            "rewritten_query": search_query,
            "fallback_triggered": should_fallback,
            "fallback_reason": reason,
            "best_internal_distance": best_dist,
            "low_confidence_threshold": retrieval.LOW_CONFIDENCE_DISTANCE,
            "num_chunks_found": len(chunks),
            "chunks": [
                {
                    "page": c["page"],
                    "section": c["section"],
                    "document": c["document"],
                    "source_url": c.get("source_url", ""),
                    "distance": c.get("distance", 0),
                    "text_snippet": c["text"][:150] + "..."
                }
                for c in chunks
            ]
        }
    except Exception as e:
        return {"error": str(e), "query": q}