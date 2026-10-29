r"""
Ingestion runner — the script you execute to build the vector store.

Why this file is separate from app/services/ingestion.py:
- services/ingestion.py is a library: pure functions, importable, testable.
- scripts/ingest.py is a runner: it configures sys.path, parses args, and executes.
- Mixing the two makes testing harder and imports fragile.

How to run:
    cd backend
    .venv\Scripts\activate        (Windows)
    python scripts/ingest.py
    python scripts/ingest.py --reset   (wipes the index first)
    python scripts/ingest.py --force   (re-ingests even if already present)

What it does:
- Reads JURISDICTIONS from app/config.py
- Optionally resets the vector store (--reset)
- For each document, skips it if its title already appears in metadata.json
- Otherwise runs the full pipeline: PDF -> chunks -> embeddings -> FAISS

Why --reset exists:
- Re-running ingestion appends vectors. On a multi-jurisdiction corpus that's
  the desired behaviour. But on a single PDF it duplicates every chunk.
- --reset gives you a clean rebuild without manually deleting files.

Why --force exists:
- If a document is already in metadata.json but you want to re-ingest it
  (e.g. after correcting a document file, or fixing a chunking bug),
  --force bypasses the skip check.
"""

import argparse
import json
import sys
from pathlib import Path

# Make `app` importable whether we run from backend/ or backend/scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config
from app.services.ingestion import ingest_document, reset_vector_store


def _load_existing_document_titles() -> set:
    """
    Read metadata.json and return the set of document titles already ingested.

    Why: appending to a growing corpus shouldn't re-embed documents that are
    already present. Without this check, every ingest run duplicates every
    prior document's chunks (e.g. 1,081 -> 2,469 vectors). The returned set
    is compared against config.py's "title" field for each document.
    """
    metadata_path = Path(config.FAISS_METADATA_PATH)
    if not metadata_path.exists():
        return set()
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        return {m.get("document", "") for m in existing if m.get("document")}
    except Exception as exc:
        print(f"[ingest] Warning: could not read existing metadata ({exc}); will ingest all.")
        return set()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the FAISS vector store from configured regulatory PDFs."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the existing FAISS index and metadata before ingesting.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest documents even if their title is already in metadata.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("Regulatory Knowledge Base — Ingestion")
    print("=" * 60)
    print(f"FAISS index:  {config.FAISS_INDEX_PATH}")
    print(f"Metadata:     {config.FAISS_METADATA_PATH}")
    print(f"Data dir:     {config.DATA_DIR}")
    print(f"Reset first:  {args.reset}")
    print(f"Force redo:   {args.force}")
    print()

    if args.reset:
        reset_vector_store()
        already_ingested = set()
        print()
    else:
        already_ingested = _load_existing_document_titles()
        if already_ingested:
            print(f"[ingest] Skipping {len(already_ingested)} already-ingested document(s).")
            print(f"[ingest] Use --force to override.\n")

    total_chunks = 0
    skipped = 0
    for jurisdiction_code, info in config.JURISDICTIONS.items():
        print(f"--- {info['regulator']} ({jurisdiction_code}) ---")
        for doc in info["documents"]:
            title = doc["title"]
            if not args.force and title in already_ingested:
                print(f"  [SKIP] Already ingested: {title}")
                skipped += 1
                continue
            print(f"  Document: {title} ({doc['file']})")
            try:
                count = ingest_document(jurisdiction_code, doc)
                total_chunks += count
            except FileNotFoundError as exc:
                print(f"  [SKIP] {exc}")
            except Exception as exc:
                print(f"  [FAIL] {type(exc).__name__}: {exc}")
                raise
        print()

    print("=" * 60)
    print(f"Ingestion complete. New chunks stored: {total_chunks}")
    print(f"Documents skipped (already present):  {skipped}")
    print("=" * 60)


if __name__ == "__main__":
    main()