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

What it does:
- Reads JURISDICTIONS from app/config.py
- Optionally resets the vector store (--reset)
- For each document, runs the full pipeline: PDF -> chunks -> embeddings -> FAISS
- Prints progress at every step so failures are easy to locate

Why --reset exists:
- Re-running ingestion appends vectors. On a multi-jurisdiction corpus that's
  the desired behaviour. But on a single PDF it duplicates every chunk.
- --reset gives you a clean rebuild without manually deleting files.

Why sys.path.insert:
- Python doesn't know where `app` is unless we're running from backend/.
- This line makes the script work no matter what directory you invoke it from.
"""

import argparse
import sys
from pathlib import Path

# Make `app` importable whether we run from backend/ or backend/scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config
from app.services.ingestion import ingest_document, reset_vector_store


def parse_args() -> argparse.Namespace:
    """CLI flags. Currently only --reset."""
    parser = argparse.ArgumentParser(
        description="Build the FAISS vector store from configured regulatory PDFs."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the existing FAISS index and metadata before ingesting.",
    )
    return parser.parse_args()


def main() -> None:
    """
    Loop through every jurisdiction and every document, ingest each one.

    Why loop over config rather than hardcode the VARA file:
    - Adding CBN later means editing config.py, then re-running this script.
    - This script never changes when jurisdictions are added.
    """
    args = parse_args()

    print("=" * 60)
    print("Regulatory Knowledge Base — Ingestion")
    print("=" * 60)
    print(f"FAISS index:  {config.FAISS_INDEX_PATH}")
    print(f"Metadata:     {config.FAISS_METADATA_PATH}")
    print(f"Data dir:     {config.DATA_DIR}")
    print(f"Reset first:  {args.reset}")
    print()

    if args.reset:
        reset_vector_store()
        print()

    total_chunks = 0
    for jurisdiction_code, info in config.JURISDICTIONS.items():
        print(f"--- {info['regulator']} ({jurisdiction_code}) ---")
        for doc in info["documents"]:
            print(f"  Document: {doc['title']} ({doc['file']})")
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
    print(f"Ingestion complete. Total chunks stored: {total_chunks}")
    print("=" * 60)


if __name__ == "__main__":
    main()