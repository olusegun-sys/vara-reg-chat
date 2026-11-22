import json
import time
from pathlib import Path
from typing import List, Dict, Any
import re

import faiss
import numpy as np
import cohere
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app import config

co = cohere.Client(api_key=config.COHERE_API_KEY)


# --- VARA PDF text cleaning ------------------------------------------------
VARA_FOOTER_MARKERS = (
    "varaconnect@vara.ae",
    "araconnect@vara.ae",
    "PO Box 9292",
    "Virtual Assets Regulatory Authority",
    "سُلطة تنظيم",          # Arabic: "Authority for Regulating"
    "صندوق بريد",           # Arabic: "PO Box"
)


def _is_arabic_only(line: str) -> bool:
    """
    Return True if the line contains Arabic script and no Latin letters.
    Why: the Arabic footer half never matches an English query, so it's pure noise.
    Lines that mix Arabic+Latin (fused by pypdf) are handled by VARA_FOOTER_MARKERS above.
    """
    has_arabic = any('\u0600' <= ch <= '\u06FF' for ch in line)
    has_latin = any('a' <= ch.lower() <= 'z' for ch in line)
    return has_arabic and not has_latin


def _is_vara_document(pdf_path: Path) -> bool:
    """Return True if this PDF is a VARA document (identified by filename prefix)."""
    return pdf_path.name.startswith("VARA_EN_")


def clean_vara_pdf_text(text: str) -> str:
    """Strip VARA page footers and Arabic-only lines from extracted PDF text."""
    kept_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(marker in line for marker in VARA_FOOTER_MARKERS):
            continue
        if _is_arabic_only(line):
            continue
        if re.fullmatch(r"\d{1,3}", line):
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines)


def _demerge_fused_words(text: str) -> str:
    """
    Insert spaces where a PDF extracted fused text with no word boundaries.
    Only called for CBN documents. See prior explanation.
    """
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", text)
    text = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", text)
    return text


# --- EU PDF text cleaning ---------------------------------------------------
# Dictionary-based shatter repair. See STATE.md §5 for the full diagnostic.
def _load_english_words() -> frozenset:
    """Load the English wordlist from backend/data/english_words.txt."""
    wordlist_path = config.DATA_DIR / "english_words.txt"
    if not wordlist_path.exists():
        print(f"[ingest] WARNING: {wordlist_path} not found; shatter repair will be skipped.")
        return frozenset()
    with open(wordlist_path, "r", encoding="utf-8") as f:
        words = frozenset(line.strip().lower() for line in f if line.strip())
    print(f"[ingest] Loaded {len(words)} English words for shatter repair.")
    return words


_ENGLISH_WORDS = None


def _get_english_words() -> frozenset:
    global _ENGLISH_WORDS
    if _ENGLISH_WORDS is None:
        _ENGLISH_WORDS = _load_english_words()
    return _ENGLISH_WORDS


def _deshatter_eu_text(text: str) -> str:
    """
    Rejoin words that the EU PDF's font metrics shattered with stray spaces.

    Algorithm (strict — only joins when the joined result is a real word):
    1. Pre-pass: join hyphenated shatters ("high-r isk" -> "high-risk").
    2. Main pass: iterate over every SPACE between two letters. For each space,
       extract the full word to the left and the full word to the right, and
       join them ONLY if the joined form is a real English word.
    3. Multi-pass: repeat up to 5 times. Each pass removes spaces, so the text
       strictly shrinks and converges.

    Only called for EU documents. VARA and CBN have their own cleaners.
    If the dictionary is missing, returns text unchanged (fail-safe).
    """
    words = _get_english_words()
    if not words:
        return text

    # Pre-pass: hyphenated shatters. "-r isk" -> "-risk". Bound is {1}.
    text = re.sub(r"(-[A-Za-z]{1})\s+([a-z]{1,20})", r"\1\2", text)

    def _left_word(s: str, i: int) -> str:
        start = i
        while start > 0 and s[start - 1].isalpha():
            start -= 1
        return s[start:i]

    def _right_word(s: str, i: int) -> str:
        end = i + 1
        while end < len(s) and s[end].isalpha():
            end += 1
        return s[i + 1:end]

    def _process_once(s: str) -> str:
        matches = list(re.finditer(r"(?<=[A-Za-z]) (?=[a-z])", s))
        if not matches:
            return s

        out = []
        last = 0
        for m in matches:
            i = m.start()
            if i < last:
                continue
            left = _left_word(s, i)
            right = _right_word(s, i)
            if left and right and (left + right).lower() in words:
                # Emit text up to (but NOT including) the left word. Why
                # `i - len(left)`: `left` is the word ending at position i,
                # so `s[last:i]` would include `left` again when we append
                # `left + right` below. Trimming the slice by len(left)
                # aligns the boundary with the start of the left word.
                out.append(s[last:i - len(left)])
                out.append(left + right)  # the joined word (only copy)
                last = i + 1 + len(right)  # skip past the right word
            else:
                out.append(s[last:i + 1])  # text up to and including space
                last = i + 1
        out.append(s[last:])
        return "".join(out)

    for _ in range(5):
        new_text = _process_once(text)
        if new_text == text:
            break
        text = new_text

    return text


def load_pdf_pages(pdf_path: Path) -> List[Dict[str, Any]]:
    pages = []
    if pdf_path.suffix.lower() == ".txt":
        try:
            with open(pdf_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            text = "".join(char for char in text if char.isprintable() or char in "\n\r\t")
            if text.strip():
                pages.append({"page": 1, "text": text})
        except Exception as e:
            print(f"[ingest] Warning: could not read {pdf_path.name}: {e}")
        return pages

    reader = PdfReader(str(pdf_path))
    for idx, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        if _is_vara_document(pdf_path):
            text = clean_vara_pdf_text(raw)
        elif pdf_path.name.startswith("cbn_"):
            text = _demerge_fused_words(raw)
        else:
            text = _deshatter_eu_text(raw)
        if len(text) < 40:
            continue
        pages.append({"page": idx, "text": text})
    return pages


def detect_section(text: str) -> str:
    match = re.search(r"(Part\s+[IVX]+|Section\s+[A-Z]|[A-Z]\.\s+[A-Z][a-z].{0,60})", text)
    return match.group(1).strip() if match else "General"


def chunk_pages(pages: List[Dict[str, Any]], chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " "],
    )
    chunks = []
    for page in pages:
        pieces = splitter.split_text(page["text"])
        for i, piece in enumerate(pieces):
            chunks.append({
                "text": piece,
                "page": page["page"],
                "section": detect_section(piece),
                "chunk_index": i,
            })
    return chunks


def embed_chunks(chunks: List[Dict[str, Any]], model_name: str = None) -> List[List[float]]:
    texts = [c["text"] for c in chunks]
    embeddings = []
    batch_size = 40
    total_batches = (len(texts) + batch_size - 1) // batch_size

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        current_batch = i // batch_size + 1
        print(f"  [embed] Processing batch {current_batch} of {total_batches}...")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = co.embed(texts=batch, model="embed-english-v3.0", input_type="search_document")
                embeddings.extend(response.embeddings)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  [embed] Batch {current_batch} failed. Retrying in 20s...")
                    time.sleep(20)
                else:
                    raise e

        if current_batch < total_batches:
            print("  [embed] Sleeping 60 seconds to respect API rate limits...")
            time.sleep(60)

    return embeddings


def reset_vector_store() -> None:
    index_path = Path(config.FAISS_INDEX_PATH)
    metadata_path = Path(config.FAISS_METADATA_PATH)
    if index_path.exists(): index_path.unlink()
    if metadata_path.exists(): metadata_path.unlink()


def store_in_faiss(chunks, embeddings, jurisdiction, regulator, document_title, effective_date) -> int:
    index_path = Path(config.FAISS_INDEX_PATH)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    vectors = np.array(embeddings, dtype="float32")
    dim = vectors.shape[1]

    if index_path.exists():
        index = faiss.read_index(str(index_path))
    else:
        index = faiss.IndexFlatL2(dim)

    index.add(vectors)
    faiss.write_index(index, str(index_path))

    metadata_path = Path(config.FAISS_METADATA_PATH)
    existing = []
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            existing = json.load(f)

    for c in chunks:
        existing.append({
            "text": c["text"],
            "jurisdiction": jurisdiction,
            "regulator": regulator,
            "document": document_title,
            "effective_date": effective_date,
            "page": c["page"],
            "section": c["section"],
            "chunk_index": c["chunk_index"],
        })

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    return len(chunks)


def ingest_document(jurisdiction: str, doc_config: Dict[str, str]) -> int:
    pdf_path = config.DATA_DIR / doc_config["file"]
    if not pdf_path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")

    print(f"[ingest] Loading {pdf_path.name}...")
    pages = load_pdf_pages(pdf_path)
    chunks = chunk_pages(pages, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    print(f"[ingest] Created {len(chunks)} chunks.")

    print("[ingest] Embedding with Cohere...")
    embeddings = embed_chunks(chunks)

    regulator = config.JURISDICTIONS[jurisdiction]["regulator"]
    count = store_in_faiss(chunks, embeddings, jurisdiction, regulator, doc_config["title"], doc_config["effective_date"])
    print(f"[ingest] Stored {count} chunks in FAISS.")
    return count


# Test harness. Run with `python -m app.services.ingestion` from backend/.
if __name__ == "__main__":
    from app.config import DATA_DIR

    sample = DATA_DIR / "EU_AI_Act_Regulation_2024_1689.pdf"
    print(f"[test] Loading page 69 from {sample.name}...")
    reader = PdfReader(str(sample))
    raw = reader.pages[68].extract_text() or ""
    cleaned = _deshatter_eu_text(raw)

    print("\n[test] BEFORE (first 600 chars):")
    print(raw[:600])
    print("\n[test] AFTER (first 600 chars):")
    print(cleaned[:600])

    print("\n[test] Spot checks — these should all be TRUE:")
    for phrase in [
        "such", "high-risk", "system", "biometric", "identification",
        "Article", "Directive", "enforcement", "purpose", "genuine",
        "In no case", "a genuine", "It shall", "This paragraph",
    ]:
        print(f"  {phrase!r}: {phrase in cleaned}")

    print("\n[test] Spot checks — these should all be FALSE (no over-joins):")
    for bad in [
        "suchhigh", "AIsyste", "enforcementpur", "criminaloffe",
        "Itsshall", "decisionthat", "Thisparagraph", "inno case",
    ]:
        print(f"  {bad!r}: {bad in cleaned}")