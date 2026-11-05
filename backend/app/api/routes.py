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


def _out_of_scope_regex() -> re.Pattern:
    """
    Build a \b-anchored regex from config.OUT_OF_SCOPE_JURISDICTION_TOKENS.
    Adding a regulator = append to the list in config.py; no code change here.
    """
    tokens = config.OUT_OF_SCOPE_JURISDICTION_TOKENS
    if not tokens:
        return re.compile(r"(?!x)x")  # never matches
    pattern = r"\b(" + "|".join(re.escape(t) for t in tokens) + r")\b"
    return re.compile(pattern, re.IGNORECASE)


_OUT_OF_SCOPE_RE = _out_of_scope_regex()


def _needs_web_fallback(question: str, chunks: list) -> tuple:
    """
    Pre-generation check. Two reasons to hit the web before asking the LLM:
      A. The question explicitly names an out-of-scope regulator.
      B. FAISS returned low-confidence chunks (question doesn't match the corpus).
    A third trigger fires AFTER generation (refusal-detection retry) — see
    _answer_refused() and the retry logic in chat() / chat_stream().
    """
    if _OUT_OF_SCOPE_RE.search(question):
        return True, "out-of-scope jurisdiction mentioned"
    if retrieval.is_low_confidence(chunks):
        best = min((c.get("distance", 99) for c in chunks), default=99)
        return True, f"low retrieval confidence (best distance={best:.3f})"
    return False, ""


def _answer_refused(answer_text: str) -> bool:
    """
    Detect whether the LLM's answer contains any refusal phrase from config.
    Used to trigger a silent web-retry so the user never sees "I don't know"
    when the web could have answered.
    """
    if not answer_text:
        return True
    lower = answer_text.lower()
    return any(pattern.lower() in lower for pattern in config.REFUSAL_PATTERNS)


def _apply_web_fallback(question: str) -> tuple:
    """
    Run the web search and return (chunks, succeeded: bool).
    If Tavily returns zero trusted sources, we return ([], False) so the caller
    knows to refuse honestly instead of falling back to internal junk.
    """
    web_chunks = web_search.search_web(question)
    if not web_chunks:
        print("[fallback] Web search returned no trusted sources. Refusing honestly.")
        return [], False
    return web_chunks, True


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

    chunks = retrieval.retrieve_chunks(search_query, req.jurisdiction)

    should_fallback, reason = _needs_web_fallback(req.question, chunks)
    if should_fallback:
        print(f"[fallback:pre] {reason}. Triggering web search.")
        # CRITICAL: when fallback fires, TRUST the fallback result — even if empty.
        # We must not silently keep the low-confidence internal chunks, because
        # that would cause the LLM to hallucinate a citation from an irrelevant page.
        chunks, _ = _apply_web_fallback(req.question)

    if not chunks:
        # Honest refusal — no internal, no trusted web source.
        refusal = (
            "No authoritative source found for this question. This tool is scoped "
            "to regulatory and compliance topics from loaded regulators and trusted "
            "web sources (official regulators and established financial press). "
            "Try asking about a specific regulator or rule."
        )
        return ChatResponse(
            answer=refusal,
            sources=[],
            session_id=req.session_id or str(uuid.uuid4()),
            model_used=config.LLM_MODEL,
        )

    try:
        answer = llm.generate_answer(req.question, chunks, req.history, req.jurisdiction)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM provider error: {str(e)}")

    # Post-generation retry: if the LLM refused and we haven't already gone to
    # the web, retry once with web results — so the user never sees a refusal
    # when the web could have answered.
    if not should_fallback and _answer_refused(answer):
        print("[fallback:post] LLM refused; retrying with web search.")
        web_chunks, ok = _apply_web_fallback(req.question)
        if ok:
            try:
                answer = llm.generate_answer(req.question, web_chunks, req.history, req.jurisdiction)
                chunks = web_chunks
            except Exception as e:
                print(f"[fallback:post] Web retry failed: {e}")

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
        print(f"[fallback:pre] {reason}. Triggering web search.")
        # Trust the fallback. If it returns empty, chunks = [] and stream_answer
        # will emit the honest refusal. No silent fallback to internal junk.
        chunks, _ = _apply_web_fallback(req.question)

    # Streaming note: we cannot retry mid-stream without the user seeing a
    # partial answer, so post-generation retry is only applied to /chat.
    return StreamingResponse(
        llm.stream_answer(req.question, chunks, req.history, req.jurisdiction),
        media_type="text/event-stream",
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
        internal_chunks = chunks
        if should_fallback:
            print(f"[debug-search fallback] {reason}. Triggering web search.")
            chunks, _ = _apply_web_fallback(q)

        best_dist = min((c.get("distance", 99) for c in internal_chunks), default=None)
        would_refuse = (len(chunks) == 0)

        return {
            "original_query": q,
            "rewritten_query": search_query,
            "fallback_triggered": should_fallback,
            "fallback_reason": reason,
            "best_internal_distance": best_dist,
            "low_confidence_threshold": retrieval.LOW_CONFIDENCE_DISTANCE,
            "num_chunks_found": len(chunks),
            "would_refuse": would_refuse,
            "chunks": [
                {
                    "page": c["page"],
                    "section": c["section"],
                    "document": c["document"],
                    "source_url": c.get("source_url", ""),
                    "authority_tier": c.get("authority_tier", ""),
                    "distance": c.get("distance", 0),
                    "text_snippet": c["text"][:150] + "..."
                }
                for c in chunks
            ],
        }
    except Exception as e:
        return {"error": str(e), "query": q}