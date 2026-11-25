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


# CHANGED 2026-11-25: content-containment check now accepts both the raw
# question (what the user actually asked) and the rewritten query (what was
# used to retrieve). The article branch runs on the RAW question, because
# "Article 13" in the user's question is the signal we care about. The
# rewriter appends article numbers from the hint map (Article 25, Article 26,
# Article 6), which are NOT in the user's question and should not trigger
# the article branch. The keyword branch runs on BOTH queries, because the
# chunks were retrieved with the rewritten query and may contain its keywords
# (which are legitimate signals of grounding) even if the raw question's
# keywords don't match.
def _contains_query_subject(
    chunks: List[Dict[str, Any]],
    raw_question: str,
    rewritten_query: str = None,
) -> bool:
    if not chunks or not raw_question:
        return False

    stopwords = {
        "what", "are", "the", "for", "is", "a", "an", "and", "or", "in", "on",
        "of", "to", "with", "by", "from", "how", "does", "do", "can", "could",
        "should", "would", "will", "this", "that", "these", "those", "was",
        "were", "been", "being", "have", "has", "had", "having", "about",
        "under", "over", "into", "via", "per", "which", "who", "whom", "whose",
        "where", "when", "why", "than", "then", "there", "their", "they",
        "article", "articles", "regulation", "regulations", "regulatory",
        "require", "requires", "required", "requirement", "requirements",
        "law", "laws", "legal", "legally", "act", "acts", "section", "sections",
        "paragraph", "paragraphs", "clause", "clauses", "provision", "provisions",
        "obligation", "obligations", "eu", "ai", "eua", "ais",
    }

    # --- Article branch: run on the RAW question only ---------------------
    # If the user asked about "Article 13", check the section field and
    # heading for Article 13. If the user asked about "Article 99" and no
    # chunk is about Article 99, we don't return False yet — the keyword
    # branch may still match on other terms. (But for a pure "Article N"
    # question with no other keywords, it'll fall through and return False,
    # which is the correct "ungrounded" result for Article 99.)
    article_match = re.search(r'\bArticle\s+(\d+[a-zA-Z]?)\b', raw_question, re.IGNORECASE)
    if article_match:
        target_num = article_match.group(1)
        target_section = "Article " + target_num
        target_phrase_prefix = ("article " + target_num).lower()

        for c in chunks:
            if (c.get("section") or "").strip() == target_section:
                return True

        for c in chunks:
            head = (c.get("text") or "")[:100].lower().lstrip()
            if head.startswith(target_phrase_prefix):
                return True
        # Article wasn't found by section/heading. Fall through to keyword
        # check. For "Article 99", the keyword branch will also fail (no
        # chunk contains "99" as a distinctive 4+ digit number, and the
        # other keywords are stopwords). For "Article 13", the chunk may
        # contain "instructions" or "transparency" — those keywords will
        # match, and the chunk is a valid grounding source even if the
        # article heading was split mid-chunk.

    # --- Numeric branch: 4+ digit numbers, run on both queries ------------
    for q in (raw_question, rewritten_query):
        if not q:
            continue
        for num in re.findall(r'\b\d+\b', q):
            if len(num) >= 4:
                for c in chunks:
                    if num in (c.get("text") or "").lower():
                        return True

    # --- Keyword branch: run on BOTH queries ------------------------------
    for q in (raw_question, rewritten_query):
        if not q:
            continue
        words = re.findall(r'\w+', q.lower())
        keywords = [w for w in words if len(w) > 3 and w not in stopwords]

        if not keywords:
            continue

        for c in chunks:
            text = (c.get("text") or "").lower()
            for kw in keywords:
                if kw in text:
                    return True

        for i in range(len(keywords) - 1):
            phrase = keywords[i] + " " + keywords[i + 1]
            for c in chunks:
                if phrase in (c.get("text") or "").lower():
                    return True

    return False


# CHANGED 2026-11-25: accepts rewritten_query so it can pass it through to
# _contains_query_subject. The raw question is the user's actual ask; the
# rewritten query is what was used for retrieval. Both are relevant to
# grounding: the raw question tells us what the user asked, the rewritten
# query tells us what the retrieval was optimized for.
def _classify_grounding(
    chunks: List[Dict[str, Any]],
    raw_question: str,
    rewritten_query: str = None,
) -> str:
    if not chunks:
        return "weak"

    if not _contains_query_subject(chunks, raw_question, rewritten_query):
        return "ungrounded"

    best = _best_distance(chunks)

    # Lexical overlap check uses the raw question's words (what the user
    # asked), not the rewritten query's, so "strong" reflects the user's
    # actual vocabulary.
    question_words = {w for w in re.findall(r'\w+', raw_question.lower()) if len(w) > 3}
    overlap_found = False
    if question_words:
        for c in chunks:
            chunk_words = set(re.findall(r'\w+', (c.get("text") or "").lower()))
            if question_words & chunk_words:
                overlap_found = True
                break

    if best <= LOW_CONFIDENCE_DISTANCE and overlap_found:
        return "strong"
    if best > LOW_CONFIDENCE_DISTANCE:
        return "weak"
    return "partial"


# CHANGED 2026-11-25: accepts rewritten_query, passes it through.
def _attach_grounding(
    chunks: List[Dict[str, Any]],
    raw_question: str,
    rewritten_query: str = None,
) -> List[Dict[str, Any]]:
    if not chunks:
        return chunks
    label = _classify_grounding(chunks, raw_question, rewritten_query)
    for c in chunks:
        c["grounding"] = label
    return chunks


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

        if title in _VARA_PART_MAPPING:
            for mapping in _VARA_PART_MAPPING[title]:
                if mapping["start"] <= page <= mapping["end"]:
                    c["section"] = mapping["section"]
                    break

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
    index, metadata = _load_index_and_metadata()

    max_retries = 3
    backoff_schedule = [5, 15, 30]
    response = None
    for attempt in range(max_retries + 1):
        try:
            response = co.embed(
                texts=[query],
                model="embed-english-v3.0",
                input_type="search_query",
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
    _, metadata = _load_index_and_metadata()
    tokenized_query = re.findall(r'\w+', query.lower())

    scores = _BM25.get_scores(tokenized_query)
    top_indices = np.argsort(scores)[::-1]

    chunks = []
    for idx in top_indices:
        if scores[idx] == 0:
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
            "distance": 1.0 / (scores[idx] + 1.0),
        })
        if len(chunks) >= top_k:
            break

    return chunks


def _reciprocal_rank_fusion(list1: List[Dict[str, Any]], list2: List[Dict[str, Any]], k: int = 60) -> List[Dict[str, Any]]:
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

    sorted_indices = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

    return [chunk_map[idx] for idx in sorted_indices]


# CHANGED 2026-11-25: added `raw_question` parameter. The live pipeline
# calls this with the REWRITTEN query as `question` and the RAW user
# question as `raw_question`. Backward compatible: if raw_question is None,
# it defaults to `question` (the old behavior, where the retrieval query
# and the grounding question were the same string).
def retrieve_chunks(
    question: str,
    jurisdiction: str,
    top_k: int = None,
    raw_question: str = None,
) -> List[Dict[str, Any]]:
    top_k = top_k or config.TOP_K_RESULTS
    index, _ = _load_index_and_metadata()
    if index.ntotal == 0:
        return []

    # If raw_question isn't provided, use `question` for both. This keeps
    # the old behavior for callers that haven't been updated yet.
    if raw_question is None:
        raw_question = question

    faiss_chunks = _search_faiss(question, jurisdiction, top_k)
    bm25_chunks = _search_bm25(question, jurisdiction, top_k)

    if faiss_chunks or bm25_chunks:
        chunks = _reciprocal_rank_fusion(faiss_chunks, bm25_chunks)
    else:
        chunks = []

    if is_low_confidence(faiss_chunks):
        print(f"[retrieval] Low FAISS confidence (dist: {_best_distance(faiss_chunks):.2f}). Attempting broader keyword search...")
        broader_query = _extract_keywords(question)

        if broader_query:
            broader_faiss = _search_faiss(broader_query, jurisdiction, top_k)
            broader_bm25 = _search_bm25(broader_query, jurisdiction, top_k)

            if broader_faiss and _best_distance(broader_faiss) < _best_distance(faiss_chunks):
                print(f"[retrieval] Broader search improved confidence (new dist: {_best_distance(broader_faiss):.2f}). Using broader results.")
                chunks = _reciprocal_rank_fusion(broader_faiss, broader_bm25)

    chunks = chunks[:top_k]

    chunks = _attach_source_urls(chunks, jurisdiction)
    # Pass both: raw_question for the content check, question (rewritten)
    # for the keyword fallback. Both are used inside _contains_query_subject.
    return _attach_grounding(chunks, raw_question, rewritten_query=question)


def get_chunk_count() -> int:
    try:
        index, _ = _load_index_and_metadata()
        return index.ntotal
    except Exception:
        return 0


# Test harness. Runs with `python -m app.services.retrieval` from backend/.
# Mirrors the LIVE pipeline: raw question -> rewrite_query() -> retrieve_chunks()
# -> grounding label. The live pipeline passes BOTH the rewritten query (for
# retrieval) and the raw question (for the content check), exactly as this
# harness does.
#
# Cost: 5 Cohere calls + 5 Groq calls (the rewriter fires for all 5 questions).
if __name__ == "__main__":
    from app.services.llm import rewrite_query

    test_cases = [
        ("A — VARA staking", "What are the staking requirements for virtual asset service providers under VARA?", "AE-Dubai", "strong"),
        ("B1 — Provider/Deployer", "We are a US company hosting a third-party hiring tool for EU customers. Are we a provider or a deployer under the EU AI Act?", "EU", "strong"),
        ("B3 — High-risk dates", "When do the high-risk AI system obligations take effect?", "EU", "strong"),
        ("B2 — Article 13", "What does Article 13 of the EU AI Act require regarding instructions for use?", "EU", "strong"),
        ("Unanswerable — Article 99", "What does Article 99 of the EU AI Act require?", "EU", "ungrounded"),
    ]

    print("=== Grounding test harness (full pipeline, mirrors live) ===")
    print("(Cost: 5 Cohere calls + 5 Groq calls for the rewriter. ~1.5k Groq tokens.)")
    print()

    passed = 0
    failed = 0
    for label, question, jurisdiction, expected in test_cases:
        try:
            rewritten = rewrite_query(question, jurisdiction)
            print(f"[harness] {label}")
            print(f"  raw question: {question!r}")
            print(f"  rewritten:    {rewritten!r}")

            # Mirror the live pipeline: pass the rewritten query for retrieval,
            # and the raw question for the content check.
            chunks = retrieve_chunks(rewritten, jurisdiction, raw_question=question)

            actual = chunks[0].get("grounding") if chunks else "NO CHUNKS"
            status = "PASS" if actual == expected else "FAIL"
            if status == "PASS":
                passed += 1
            else:
                failed += 1

            print(f"  expected: {expected}, actual: {actual}, chunks: {len(chunks)}")
            if chunks:
                print(f"  top: {chunks[0].get('document', '?')} p.{chunks[0].get('page', '?')} section={chunks[0].get('section', '?')!r}")
                print(f"  top chunk text (first 200 chars): {chunks[0].get('text', '')[:200]!r}")
            print()
        except Exception as e:
            failed += 1
            print(f"ERROR: {label}: {e}")
            print()

    print(f"=== {passed} passed, {failed} failed ===")