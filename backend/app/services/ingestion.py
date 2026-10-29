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
# Why this exists: every VARA PDF page repeats the same Arabic+English footer
# ("varaconnect@vara.ae - PO Box 9292...") and a standalone page number. Without
# stripping it, those lines get chunked and embedded hundreds of times, polluting
# the index with near-duplicate noise that steals top_k slots from real rule text.
# Also drops pages whose only content was a table rendered as "1 1 1 1 1 ...".
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


def clean_vara_pdf_text(text: str) -> str:
    """
    Strip VARA page footers and Arabic-only lines from extracted PDF text.
    Called only on the PDF branch — the .txt branch of load_pdf_pages() is untouched.
    """
    kept_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        # Drop empty lines that survive after other filters
        if not line:
            continue
        # Drop any line containing a known footer marker (substring match)
        if any(marker in line for marker in VARA_FOOTER_MARKERS):
            continue
        # Drop lines that are Arabic-only (no Latin letters at all)
        if _is_arabic_only(line):
            continue
        # Drop standalone page numbers (e.g. "5" or "36" left over after footer strip)
        if re.fullmatch(r"\d{1,3}", line):
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines)


def load_pdf_pages(pdf_path: Path) -> List[Dict[str, Any]]:
    pages = []
    if pdf_path.suffix.lower() == ".txt":
        try:
            # errors="replace" prevents crashing on weird binary characters
            with open(pdf_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            # Strip out null bytes and non-printable garbage
            text = "".join(char for char in text if char.isprintable() or char in "\n\r\t")
            if text.strip():
                pages.append({"page": 1, "text": text})
        except Exception as e:
            print(f"[ingest] Warning: could not read {pdf_path.name}: {e}")
        return pages

    reader = PdfReader(str(pdf_path))
    for idx, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        # Clean footers BEFORE checking emptiness — otherwise a page whose only
        # text was the footer would slip through and become a useless chunk.
        text = clean_vara_pdf_text(raw)
        # Drop pages whose remaining content is too short to be a real rule
        # (typically pypdf's mis-rendered table pages: "1 1 1 1 1 ...").
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