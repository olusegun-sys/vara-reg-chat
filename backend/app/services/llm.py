import json
import time
from typing import List, Dict, Any
from openai import OpenAI

from app import config

SYSTEM_PROMPT = """You are a regulatory compliance assistant.
Answer the user's question using ONLY the context provided below.
Cite the page number and section for every claim you make.

CITATION RULES — follow these exactly:
1. Every citation MUST name the rulebook the rule comes from. Do NOT write "[Page 15, A.1]". Write "[Exchange Services Rulebook, p.15]" or "[Broker-Dealer Services Rulebook, p.15]" or "[Custody Services Rulebook, p.17]".
2. The rulebook name comes from the "Document:" line in the context block for each chunk. Use the exact document title from that line.
3. Some rulebooks share identical section numbers and near-identical language. Specifically:
   - Part IV (Margin Trading) exists in BOTH the Exchange Services Rulebook AND the Broker-Dealer Services Rulebook.
   - Part V (ETD Services / Collateral Wallet Services) exists in BOTH the Exchange Services Rulebook AND the Custody Services Rulebook, with different content.
   When a chunk covers a shared section number, you MUST say which rulebook it is from. If the user's question touches on either, cite the correct rulebook — do NOT combine citations from both unless the answer genuinely requires both.
4. If you cannot determine which rulebook a chunk belongs to, do NOT cite that chunk. Drop it and answer from the chunks whose rulebook you can identify.
5. Do not invent page numbers, section numbers, rulebook names, or any other citation detail.

If the answer is not contained in the context, respond exactly:
"I don't have that information in the provided document."

Be precise, concise, and never speculate."""


def _build_context(chunks: List[Dict[str, Any]]) -> str:
    parts = []
    for c in chunks:
        parts.append(f"[Page {c['page']} | {c['section']} | {c['document']}]\n{c['text']}")
    return "\n\n---\n\n".join(parts)


def _build_user_message(question: str, chunks: List[Dict[str, Any]]) -> str:
    context = _build_context(chunks)
    return f"""CONTEXT:
{context}

QUESTION: {question}"""


def _get_client() -> OpenAI:
    return OpenAI(
        api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
        timeout=60.0,
    )


def rewrite_query(question: str) -> str:
    client = _get_client()
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.0,
            max_tokens=60,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a search query optimizer for a VARA compliance database. "
                               "Take the user's question and rewrite it into a short, keyword-rich search query. "
                               "Expand vague terms into regulatory synonyms (e.g., 'capital' -> 'Paid-Up Capital'). "
                               "Output ONLY the rewritten query."
                },
                {"role": "user", "content": question}
            ],
        )
        rewritten = response.choices[0].message.content.strip()
        print(f"[query_rewrite] '{question}' -> '{rewritten}'")
        return rewritten
    except Exception as e:
        print(f"[query_rewrite] Failed: {e}")
        return question


def generate_answer(question: str, chunks: List[Dict[str, Any]], history: List[Dict[str, str]] = None) -> str:
    if not chunks:
        return "I don't have that information in the provided document."

    client = _get_client()
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if history:
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
    messages.append({"role": "user", "content": _build_user_message(question, chunks)})

    try:
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS,
            messages=messages,
        )
    except Exception as exc:
        print(f"[llm] Generate failed, retrying: {exc}")
        time.sleep(1)
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS,
            messages=messages,
        )

    content = response.choices[0].message.content
    return (content or "").strip()


def stream_answer(question: str, chunks: List[Dict[str, Any]], history: List[Dict[str, str]] = None):
    if not chunks:
        yield f"data: {json.dumps({'type': 'text', 'text': 'I don\'t have that information in the provided document.'})}\n\n"
        return

    # NEW: Include source_url in the stream so the frontend can make clickable links
    sources_data = [
        {
            "page": c["page"],
            "section": c["section"],
            "document": c["document"],
            "source_url": c.get("source_url", ""),
        } 
        for c in chunks
    ]
    yield f"data: {json.dumps({'type': 'sources', 'sources': sources_data})}\n\n"

    client = _get_client()
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if history:
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
    messages.append({"role": "user", "content": _build_user_message(question, chunks)})
    
    try:
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS,
            stream=True,
            messages=messages,
        )
        
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                yield f"data: {json.dumps({'type': 'text', 'text': text})}\n\n"
                
    except Exception as exc:
        error_msg = f"⚠️ LLM streaming error: {str(exc)}"
        yield f"data: {json.dumps({'type': 'text', 'text': error_msg})}\n\n"


def generate_title(question: str) -> str:
    client = _get_client()
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            temperature=0.3, 
            max_tokens=20,   
            messages=[
                {"role": "system", "content": "Generate a short 3-5 word title. Output ONLY the title."},
                {"role": "user", "content": f"Question: {question}"}
            ],
        )
        title = response.choices[0].message.content.strip()
        title = title.replace('"', '').replace("'", "").replace("*", "")
        return title if title else question[:30]
    except Exception as e:
        print(f"[title] Failed: {e}")
        return question[:30].strip() + "..." if len(question) > 30 else question