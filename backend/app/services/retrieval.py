import json
import urllib.parse
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


# --- Confidence threshold ---------------------------------------------------
# Why: FAISS with embed-english-v3.0 returns squared L2 distances (lower=better).
# A "good" match in a regulatory corpus typically lands around 0.4–0.9. A "junk"
# match (question has nothing to do with the corpus) typically lands at 1.2+.
# We treat anything above LOW_CONFIDENCE_DISTANCE as "not really a match" and
# let the route layer decide to fall back to web search.
# NOTE: this number is a starting value. Tune it after running 10-20 real
# queries through /debug-search and comparing good vs junk results.
LOW_CONFIDENCE_DISTANCE = 1.15


def _best_distance(chunks: List[Dict[str, Any]]) -> float:
    """
    Return the smallest (best) distance among the chunks, or +inf if empty.
    Why: a fallback trigger needs a single scalar to compare against a threshold.
    """
    if not chunks:
        return float("inf")
    return min(c.get("distance", float("inf")) for c in chunks)


def is_low_confidence(chunks: List[Dict[str, Any]]) -> bool:
    """
    Return True when the retrieval result is not confident enough to trust.
    Used by routes.py to decide whether to invoke web search fallback.
    Exposed as a public function so routes.py doesn't have to reimplement logic.
    """
    return _best_distance(chunks) > LOW_CONFIDENCE_DISTANCE


# --- VARA "Part" Mapping ---------------------------------------------------
# Why: Terry wants to see the exact "Part" (e.g., Part 3, Part 1A) in the UI.
# The PDFs do not contain this text in a machine-readable way. We map page
# ranges to Part names here.
# NOTE: You must update the start/end pages to match the actual VARA PDFs.
_VARA_PART_MAPPING = {
    "Exchange Services Rulebook": [
        {"start": 1, "end": 20, "section": "Part 1 (General)"},
        {"start": 21, "end": 40, "section": "Part 2 (Licensing)"},
        {"start": 41, "end": 60, "section": "Part 3 (Market Surveillance)"},
    ],
    "Custody Services Rulebook": [
        {"start": 1, "end": 15, "section": "Part 1 (General)"},
        {"start": 16, "end": 35, "section": "Part 2 (Client Assets)"},
    ],
    "Compliance and Risk Management Rulebook": [
        {"start": 1, "end": 10, "section": "Part 1 (General)"},
        {"start": 11, "end": 30, "section": "Part 2 (AML/CFT)"},
    ]
}


def _attach_source_urls(chunks: List[Dict[str, Any]], jurisdiction: str) -> List[Dict[str, Any]]:
    """
    Enrich each chunk dict with the source_url of its parent document.
    Also injects VARA "Part" numbers into the section field, and appends
    #page=X&search=Y to PDF URLs so the browser jumps to the exact page
    and highlights the exact text.
    """
    registry = config.JURISDICTIONS.get(jurisdiction, {}).get("documents", [])
    url_by_title = {d["title"]: d.get("source_url", "") for d in registry}

    for c in chunks:
        title = c.get("document", "")
        page = c.get("page", 1)
        url = url_by_title.get(title, "")

        # 1. Inject the VARA "Part" name if we have a mapping for this doc
        if title in _VARA_PART_MAPPING:
            for mapping in _VARA_PART_MAPPING[title]:
                if mapping["start"] <= page <= mapping["end"]:
                    c["section"] = mapping["section"]
                    break

        # 2. Deep Linking & Text Highlighting for PDFs
        if url and url.lower().endswith('.pdf') and page > 1:
            # Take the first 50 characters of the chunk text to use as a search string.
            # Why 50? Long enough to be unique, short enough to URL encode safely.
            # We strip newlines so the search parameter doesn't break.
            search_phrase = c.get("text", "")[:50].replace("\n", " ").strip()

            # URL encode the phrase so it's safe for browsers
            encoded_phrase = urllib.parse.quote(search_phrase)

            # Append BOTH page jump and search highlight
            # Format: #page=53&search="Due skill, care and diligence"
            url = f"{url}#page={page}&search=%22{encoded_phrase}%22"

        c["source_url"] = url
    return chunks


def retrieve_chunks(question: str, jurisdiction: str, top_k: int = None) -> List[Dict[str, Any]]:
    top_k = top_k or config.TOP_K_RESULTS
    index, metadata = _load_index_and_metadata()
    if index.ntotal == 0:
        return []

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