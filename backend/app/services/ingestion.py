import json
from pathlib import Path
from typing import List, Dict, Any
import re

import faiss
import numpy as np
import google.generativeai as genai
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app import config

genai.configure(api_key=config.GEMINI_API_KEY)

def load_pdf_pages(pdf_path: Path) -> List[Dict[str, Any]]:
    reader = PdfReader(str(pdf_path))
    pages = []
    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
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
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=batch,
            task_type="retrieval_document"
        )
        embeddings.extend(result['embedding'])
    return embeddings

def reset_vector_store() -> None:
    index_path = Path(config.FAISS_INDEX_PATH)
    metadata_path = Path(config.FAISS_METADATA_PATH)
    removed = []
    if index_path.exists():
        index_path.unlink()
        removed.append(str(index_path))
    if metadata_path.exists():
        metadata_path.unlink()
        removed.append(str(metadata_path))
    if removed:
        print(f"[reset] Deleted: {', '.join(removed)}")

def store_in_faiss(chunks, embeddings, jurisdiction, regulator, document_title, effective_date) -> int:
    index_path = Path(config.FAISS_INDEX_PATH)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    vectors = np.array(embeddings, dtype="float32")
    dim = vectors.shape[1]

    if index_path.exists():
        index = faiss.read_index(str(index_path))
        if index.d != dim:
            raise ValueError(f"Dimension mismatch: existing={index.d}, new={dim}")
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
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"[ingest] Loading {pdf_path.name}...")
    pages = load_pdf_pages(pdf_path)
    print(f"[ingest] Extracted {len(pages)} pages.")

    chunks = chunk_pages(pages, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    print(f"[ingest] Created {len(chunks)} chunks.")

    print("[ingest] Embedding with Gemini (cloud, no local model)...")
    embeddings = embed_chunks(chunks)
    print(f"[ingest] Generated {len(embeddings)} embeddings.")

    regulator = config.JURISDICTIONS[jurisdiction]["regulator"]
    count = store_in_faiss(chunks, embeddings, jurisdiction, regulator, doc_config["title"], doc_config["effective_date"])
    print(f"[ingest] Stored {count} chunks in FAISS.")
    return count