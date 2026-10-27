import json
from typing import List, Dict, Any

import faiss
import numpy as np
import google.generativeai as genai

from app import config

genai.configure(api_key=config.GEMINI_API_KEY)

def _load_index_and_metadata() -> tuple:
    try:
        index = faiss.read_index(config.FAISS_INDEX_PATH)
    except Exception as exc:
        raise RuntimeError(f"Could not load FAISS index: {exc}") from exc

    try:
        with open(config.FAISS_METADATA_PATH, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except Exception as exc:
        raise RuntimeError(f"Could not load metadata: {exc}") from exc

    return index, metadata

def retrieve_chunks(question: str, jurisdiction: str, top_k: int = None) -> List[Dict[str, Any]]:
    top_k = top_k or config.TOP_K_RESULTS
    index, metadata = _load_index_and_metadata()
    if index.ntotal == 0:
        return []

    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=question,
        task_type="retrieval_query"
    )
    query_vec = np.array([result['embedding']], dtype="float32")

    if query_vec.shape[1] != index.d:
        raise ValueError(f"Embedding dimension mismatch: index={index.d}, query={query_vec.shape[1]}")

    candidates = min(top_k * 5, index.ntotal)
    distances, indices = index.search(query_vec, candidates)

    chunks: List[Dict[str, Any]] = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(metadata):
            continue
        meta = metadata[idx]
        if meta.get("jurisdiction") != jurisdiction:
            continue
        chunks.append({
            "text": meta["text"],
            "page": meta.get("page", 0),
            "section": meta.get("section", "General"),
            "document": meta.get("document", "Unknown"),
            "distance": float(dist),
        })
        if len(chunks) >= top_k:
            break
    return chunks

def get_chunk_count() -> int:
    try:
        index, _ = _load_index_and_metadata()
        return index.ntotal
    except Exception:
        return 0