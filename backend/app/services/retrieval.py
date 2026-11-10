import json
import urllib.parse
import re
import time
from typing import List, Dict, Any

import faiss
import numpy as np
import cohere
from rank_bm25 import BM25Okapi

from app import config

# Initialize Cohere client
co = cohere.Client(api_key=config.COHERE_API_KEY)

# --- Module-level cache -----------------------------------------------------
_INDEX = None
_METADATA = None
_BM25 = None
_TOKENIZED_CORPUS = None

def _load_index_and_metadata() -> tuple:
    global _INDEX, _METADATA, _BM25, _TOKENIZED_CORPUS
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

    # Build the BM25 index for exact keyword matching
    print(f"[retrieval] Building BM25 index over {len(_METADATA)} chunks...")
    _TOKENIZED_CORPUS = [re.findall(r'\w+', m["text"].lower()) for m in _METADATA]
    _BM25 = BM25Okapi(_TOKENIZED_CORPUS)

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
    stopwords = {"what", "are", "the", "for", "is", "a", "an", "and", "or", "in", "on", "of", "to", "with", "by", "from", "how", "does", "do", "can", "could", "should", "would"}
    words = re.findall(r'\b\w+\b', text.lower())
    filtered = [w for w in words if w not in stopwords and len(w) > 2]
    return " ".join(filtered)


def _search_faiss(query: str, jurisdiction: str, top_k: int) -> List[Dict[str, Any]]:
    """Internal helper to embed a query and search FAISS."""
    index, metadata = _load_index_and_metadata()

    # Retry with exponential backoff — Cohere free tier occasionally times out
    # on the first attempt. Four attempts with increasing waits (5s, 15s, 30s)
    # catch transient hiccups without hanging the request too long.
    # Total worst-case wait if all fail: 5 + 15 + 30 = 50 seconds of backoff,
    # plus up to 4 × 15s timeout per attempt. This is bounded and predictable.
    #
    # Why 3 retries (4 total attempts): a 20-second Cohere blip (which we have
    # seen) exhausts the old 2-retry schedule (5s + 10s + 15s timeout ≈ 30s)
    # before Cohere recovers. The new schedule gives a 20-second blip a real
    # chance to succeed on the 3rd attempt (after 5s + 15s = 20s wait).
    max_retries = 3
    backoff_schedule = [5, 15, 30]  # seconds between retries
    response = None
    for attempt in range(max_retries + 1):
        try:
            response = co.embed(
                texts=[query],
                model="embed-english-v3.0",
                input_type="search_query",
                # Timeout per attempt — keeps a single hung call from blocking forever
                request_options={"timeout_in_seconds": 15.0}
            )
            break
        except Exception as e:
            if attempt < max_retries:
                wait = backoff_schedule[attempt]
                print(f"[retrieval] Cohere embed failed (attempt {attempt+1}/{max_retries+1}): {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"[retrieval] Cohere embed failed after {max_retries+1} attempts. Raising.")
                raise RuntimeError(
                    "The embedding service (Cohere) is temporarily unreachable. "
                    "Please try again in 60 seconds. If this persists, check your internet connection."
                ) from e

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
            "id": int(idx),
            "text": meta["text"],
            "page": meta.get("page", 0),
            "section": meta.get("section", "General"),
            "document": meta.get("document", "Unknown"),
            "distance": float(dist),
        })
        if len(chunks) >= top_k:
            break
            
    return chunks


def _search_bm25(query: str, jurisdiction: str, top_k: int) -> List[Dict[str, Any]]:
    """Search the BM25 index for exact keyword matches."""
    _, metadata = _load_index_and_metadata()
    tokenized_query = re.findall(r'\w+', query.lower())
    
    # Get scores for all docs
    scores = _BM25.get_scores(tokenized_query)
    
    # Sort indices by score descending
    top_indices = np.argsort(scores)[::-1]
    
    chunks = []
    for idx in top_indices:
        if scores[idx] == 0: # Stop if scores drop to 0 (no keyword match)
            break
        meta = metadata[idx]
        if meta.get("jurisdiction") != jurisdiction:
            continue
        chunks.append({
            "id": int(idx),
            "text": meta["text"],
            "page": meta.get("page", 0),
            "section": meta.get("section", "General"),
            "document": meta.get("document", "Unknown"),
            "distance": 1.0 / (scores[idx] + 1.0), # Convert BM25 score to a distance-like metric
        })
        if len(chunks) >= top_k:
            break
            
    return chunks


def _reciprocal_rank_fusion(list1: List[Dict[str, Any]], list2: List[Dict[str, Any]], k: int = 60) -> List[Dict[str, Any]]:
    """
    Merge two ranked lists using RRF.
    This combines semantic meaning (FAISS) with exact keyword matching (BM25).
    """
    rrf_scores = {}
    chunk_map = {}
    
    for rank, chunk in enumerate(list1):
        idx = chunk["id"]
        chunk_map[idx] = chunk
        rrf_scores[idx] = rrf_scores.get(idx, 0) + 1.0 / (k + rank + 1)
        
    for rank, chunk in enumerate(list2):
        idx = chunk["id"]
        chunk_map[idx] = chunk
        rrf_scores[idx] = rrf_scores.get(idx, 0) + 1.0 / (k + rank + 1)
        
    # Sort by RRF score descending
    sorted_indices = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
    
    # Return the merged chunks
    return [chunk_map[idx] for idx in sorted_indices]


def retrieve_chunks(question: str, jurisdiction: str, top_k: int = None) -> List[Dict[str, Any]]:
    top_k = top_k or config.TOP_K_RESULTS
    index, _ = _load_index_and_metadata()
    if index.ntotal == 0:
        return []

    # 1. Dual Search (FAISS + BM25)
    faiss_chunks = _search_faiss(question, jurisdiction, top_k)
    bm25_chunks = _search_bm25(question, jurisdiction, top_k)

    # 2. Reciprocal Rank Fusion
    if faiss_chunks or bm25_chunks:
        chunks = _reciprocal_rank_fusion(faiss_chunks, bm25_chunks)
    else:
        chunks = []

    # 3. Check Confidence (using FAISS distance)
    # We check if the best FAISS result was poor. If so, we broaden and try again.
    if is_low_confidence(faiss_chunks):
        print(f"[retrieval] Low FAISS confidence (dist: {_best_distance(faiss_chunks):.2f}). Attempting broader keyword search...")
        broader_query = _extract_keywords(question)
        
        if broader_query:
            broader_faiss = _search_faiss(broader_query, jurisdiction, top_k)
            broader_bm25 = _search_bm25(broader_query, jurisdiction, top_k)
            
            # If the broader search improved the FAISS distance, use the new merged set
            if broader_faiss and _best_distance(broader_faiss) < _best_distance(faiss_chunks):
                print(f"[retrieval] Broader search improved confidence (new dist: {_best_distance(broader_faiss):.2f}). Using broader results.")
                chunks = _reciprocal_rank_fusion(broader_faiss, broader_bm25)

    # 4. Trim to top_k
    chunks = chunks[:top_k]
    
    return _attach_source_urls(chunks, jurisdiction)


def get_chunk_count() -> int:
    try:
        index, _ = _load_index_and_metadata()
        return index.ntotal
    except Exception:
        return 0