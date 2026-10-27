"""
LLM interaction: build prompt from retrieved chunks, call the configured provider.
"""
import json
import time
from typing import List, Dict, Any
from openai import OpenAI

from app import config

SYSTEM_PROMPT = """You are a regulatory compliance assistant.
Answer the user's question using ONLY the context provided below.
Cite the page number and section for every claim you make.
If the answer is not contained in the context, respond exactly:
"I don't have that information in the provided document."

Be precise, concise, and never speculate."""


def _build_context(chunks: List[Dict[str, Any]]) -> str:
    parts = []
    for c in chunks:
        parts.append(f"[Page {c['page']} | {c['section']}]\n{c['text']}")
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


def generate_answer(question: str, chunks: List[Dict[str, Any]]) -> str:
    if not chunks:
        return "I don't have that information in the provided document."

    client = _get_client()

    try:
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_message(question, chunks)},
            ],
        )
    except Exception as exc:
        # Retry once for network blips
        print(f"[llm] Generate failed, retrying: {exc}")
        time.sleep(1)
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_message(question, chunks)},
            ],
        )

    content = response.choices[0].message.content
    return (content or "").strip()


def stream_answer(question: str, chunks: List[Dict[str, Any]]):
    if not chunks:
        yield f"data: {json.dumps({'type': 'text', 'text': 'I don\'t have that information in the provided document.'})}\n\n"
        return

    sources_data = [
        {"page": c["page"], "section": c["section"], "document": c["document"]} 
        for c in chunks
    ]
    yield f"data: {json.dumps({'type': 'sources', 'sources': sources_data})}\n\n"

    client = _get_client()
    
    try:
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS,
            stream=True,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_message(question, chunks)},
            ],
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
                {"role": "system", "content": "You generate short 3-5 word titles for chat conversations. Output ONLY the title, no quotes, no punctuation, no markdown. Just the words."},
                {"role": "user", "content": f"Question: {question}"}
            ],
        )
        title = response.choices[0].message.content.strip()
        title = title.replace('"', '').replace("'", "").replace("*", "")
        return title if title else question[:30]
    except Exception as e:
        print(f"[title] LLM generation failed: {e}")
        return question[:30].strip() + "..." if len(question) > 30 else question