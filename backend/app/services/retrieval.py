import json
import urllib.parse
import re
from typing import List, Dict, Any

import faiss
import numpy as np
import cohere

from app import config

# Initialize Cohere client
co = cohere.Client(api_key=config.COHERE_API_KEY)

# --- Module-level cache -----------------------------------------------------
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
LOW_CONFIDENCE_DISTANCE = 1.15

def _best_distance(chunks: List[Dict[str, Any]]) -> float:
    if not chunks:
        return float("inf")
    return min(c.get("distance", float("inf")) for c in chunks)


def is_low_confidence(chunks: List[Dict[str, Any]]) -> bool:
    return _best_distance(chunks) > LOW_CONFIDENCE_DISTANCE


# --- VARA "Part" Mapping ---------------------------------------------------
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
            search_phrase = c.get("text", "")[:50].replace("\n", " ").strip()
            encoded_phrase = urllib.parse.quote(search_phrase)
            url = f"{url}#page={page}&search=%22{encoded_phrase}%22"

        c["source_url"] = url
    return chunks


def _extract_keywords(text: str) -> str:
    """
    Strips filler words to create a broader search query if the primary
    search fails. e.g. "What are the rules for high risk AI systems?" -> "rules high risk AI systems"
    """
    stopwords = {"what", "are", "the", "for", "is", "a", "an", "and", "or", "in", "on", "of", "to", "with", "by", "from", "how", "does", "do", "can", "could", "should", "would"}
    words = re.findall(r'\b\w+\b', text.lower())
    filtered = [w for w in words if w not in stopwords and len(w) > 2]
    return " ".join(filtered)


def _search_faiss(query: str, jurisdiction: str, top_k: int) -> List[Dict[str, Any]]:
    """Internal helper to embed a query and search FAISS."""
    index, metadata = _load_index_and_metadata()
    
    response = co.embed(
        texts=[query],
        model="embed-english-v3.0",
        input_type="search_query"
    )
    query_vec = np.array(response.embeddings, dtype="float32")

    if query_vec.shape[1] != index.d:
        raise ValueError(f"Embedding dimension mismatch: index={index.d}, query={query_vec.shape[1]}")

    candidates = min(top_k * 5, index.ntotal)
    distances, indices = index.search(query_vec, candidates)

    chunks = []
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


def retrieve_chunks(question: str, jurisdiction: str, top_k: int = None) -> List[Dict[str, Any]]:
    top_k = top_k or config.TOP_K_RESULTS
    index, _ = _load_index_and_metadata()
    if index.ntotal == 0:
        return []

    # 1. Primary Search
    chunks = _search_faiss(question, jurisdiction, top_k)

    # 2. Check Confidence
    if is_low_confidence(chunks):
        print(f"[retrieval] Low confidence (dist: {_best_distance(chunks):.2f}). Attempting broader keyword search...")
        
        # 3. Broaden the query by stripping filler words
        broader_query = _extract_keywords(question)
        if broader_query:
            broader_chunks = _search_faiss(broader_query, jurisdiction, top_k)
            
            # If the broader search actually found something better, use it.
            if broader_chunks and _best_distance(broader_chunks) < _best_distance(chunks):
                print(f"[retrieval] Broader search improved confidence (new dist: {_best_distance(broader_chunks):.2f}). Using broader results.")
                chunks = broader_chunks
            else:
                print(f"[retrieval] Broader search did not improve results (dist: {_best_distance(broader_chunks):.2f}). Sticking with original.")
        else:
            print(f"[retrieval] Could not extract keywords for broader search. Sticking with original.")

    return _attach_source_urls(chunks, jurisdiction)


def get_chunk_count() -> int:
    try:
        index, _ = _load_index_and_metadata()
        return index.ntotal
    except Exception:
        return 0