import json
from typing import List, Dict, Any

import faiss
import numpy as np
import cohere

from app import config

# Initialize Cohere client
co = cohere.Client(api_key=config.COHERE_API_KEY)

# --- Module-level cache -----------------------------------------------------
# Why: _load_index_and_metadata() reads a ~2MB FAISS index and ~3MB metadata
# JSON on EVERY query. That's ~250-400ms of disk I/O per request with no
# benefit — the files only change when you re-ingest. Cache them in module
# memory (loaded once per process, shared across all requests) for a
# one-time cost and near-instant lookups thereafter.
#
# IMPORTANT: after running `ingest.py --reset`, restart the backend process
# so this cache is invalidated. Render does this automatically on redeploy.
_INDEX = None
_METADATA = None


def _load_index_and_metadata() -> tuple:
    global _INDEX, _METADATA
    if _INDEX is not None and _METADATA is not None:
        return _INDEX, _METADATA

    try:
        _INDEX = faiss.read_index(config.FAISS_INDEX_PATH)
    except Exception as exc:
        raise RuntimeError(f"Could not load FAISS index: {exc}") from exc

    try:
        with open(config.FAISS_METADATA_PATH, "r", encoding="utf-8") as f:
            _METADATA = json.load(f)
    except Exception as exc:
        raise RuntimeError(f"Could not load metadata: {exc}") from exc

    print(f"[retrieval] Loaded {_INDEX.ntotal} vectors + {len(_METADATA)} metadata entries into memory.")
    return _INDEX, _METADATA


def _attach_source_urls(chunks: List[Dict[str, Any]], jurisdiction: str) -> List[Dict[str, Any]]:
    """
    Enrich each chunk dict with the source_url of its parent document.
    Why: the FAISS metadata doesn't store URLs. Rather than re-ingest 1,388
    chunks just to add one field, we look up the URL by matching the chunk's
    `document` title against the document registry in config.
    """
    registry = config.JURISDICTIONS.get(jurisdiction, {}).get("documents", [])
    url_by_title = {d["title"]: d.get("source_url", "") for d in registry}
    for c in chunks:
        c["source_url"] = url_by_title.get(c.get("document", ""), "")
    return chunks


def retrieve_chunks(question: str, jurisdiction: str, top_k: int = None) -> List[Dict[str, Any]]:
    top_k = top_k or config.TOP_K_RESULTS
    index, metadata = _load_index_and_metadata()
    if index.ntotal == 0:
        return []

    # Cohere embed — unavoidable ~150-250ms. Could be parallelized with the
    # query rewriter in llm.py for further speedup, but that's a bigger
    # refactor. Caching index is the biggest single win.
    response = co.embed(
        texts=[question],
        model="embed-english-v3.0",
        input_type="search_query"
    )
    query_vec = np.array(response.embeddings, dtype="float32")

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

    return _attach_source_urls(chunks, jurisdiction)


def get_chunk_count() -> int:
    try:
        index, _ = _load_index_and_metadata()
        return index.ntotal
    except Exception:
        return 0