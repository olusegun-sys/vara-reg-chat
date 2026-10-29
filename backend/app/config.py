"""
Central configuration for the Regulatory Knowledge Base Chat.

Why this file exists:
- Every path, provider setting, and magic number lives here — nowhere else.
- Adding a new regulator (CBN, FCA, etc.) means editing JURISDICTIONS, nothing else.
- Switching LLM providers (Groq -> DeepSeek) means editing .env, nothing else.
- Switching vector stores (FAISS -> Qdrant) means editing the path settings here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env into the process environment. Must run before any os.getenv calls.
load_dotenv()

# --- Paths ---
# BASE_DIR points to the backend/ folder regardless of where Python is run from.
# Why: relative paths like ./data break if someone runs the script from a different directory.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# --- LLM Provider Settings (OpenAI-compatible) ---
# .strip() is crucial here. It removes accidental trailing spaces or newlines
# that can happen when copying/pasting keys into dashboards like Render.
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b").strip()
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))

# --- Embeddings (Cohere) ---
# We use Cohere to avoid PyTorch RAM overhead and strict rate limits.
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "").strip()
EMBEDDING_MODEL = "embed-english-v3.0"

# --- Vector Store (FAISS) ---
FAISS_INDEX_PATH = os.getenv(
    "FAISS_INDEX_PATH",
    str(BASE_DIR / "faiss_index" / "index.faiss"),
)
FAISS_METADATA_PATH = os.getenv(
    "FAISS_METADATA_PATH",
    str(BASE_DIR / "faiss_index" / "metadata.json"),
)

# --- Chunking & Retrieval ---
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "7"))

# --- Jurisdiction Registry ---
JURISDICTIONS = {
    "AE-Dubai": {
        "regulator": "VARA",
        "name": "Dubai Virtual Assets Regulatory Authority",
        "documents": [
            # ================================================================
            # STATE AS OF 2026-10-29: 11 documents active.
            # FAISS index on disk contains 1,081 vectors — 487 from the original
            # 4 .txt rulebooks + 594 from the 7 new .pdf rulebooks/guidance.
            #
            # Why all 11 stay active here:
            # - This list is the SOURCE OF TRUTH for a --reset rebuild.
            # - If we ever need to rebuild from scratch, running
            #   `python scripts/ingest.py --reset` must reproduce the full
            #   1,081-chunk corpus, not a partial one.
            # - The list has no effect at query time. The running app reads
            #   faiss_index/index.faiss + metadata.json, not this list.
            # ================================================================

            # --- Existing 4 core rulebooks (originally built the 487 chunks) ---
            # Why .txt: pre-converted to clean UTF-8 by fix_text.py (STATE.md roadblock #13).
            # Do not convert these back to .pdf — the .txt versions are the canonical,
            # already-clean sources. pypdf PDF extraction would re-introduce footers.
            {
                "file": "vara_compliance_risk_rulebook.txt",
                "title": "Compliance and Risk Management Rulebook",
                "effective_date": "2025-05-19",
            },
            {
                "file": "vara_company_rulebook.txt",
                "title": "Company Rulebook",
                "effective_date": "2025-05-19",
            },
            {
                "file": "vara_technology_rulebook.txt",
                "title": "Technology and Information Rulebook",
                "effective_date": "2025-05-19",
            },
            {
                "file": "vara_market_conduct_rulebook.txt",
                "title": "Market Conduct Rulebook",
                "effective_date": "2025-05-19",
            },

            # --- NEW: 7 VA Activity Rulebooks + Guidance (PDFs, added 2026-10-29) ---
            # Why .pdf: original source PDFs. pypdf reads them natively — no .txt
            # conversion needed. ingestion.py's clean_vara_pdf_text() strips VARA
            # page footers (Arabic + "varaconnect@vara.ae" + page number) before
            # chunking, and drops pages that were just "1 1 1 1 ..." table garbage.
            # Why per-doc effective_date: each document has its own issuance date
            # encoded in the filename (VER20250519, VER20260331, VER1). Hardcoding
            # 2025-05-19 for all seven would produce false citations in the demo.
            {
                "file": "VARA_EN_258_VER20260331.pdf",
                "title": "Exchange Services Rulebook",
                "effective_date": "2026-03-31",
            },
            {
                "file": "VARA_EN_279_VER20250519.pdf",
                "title": "Lending and Borrowing Services Rulebook",
                "effective_date": "2025-05-19",
            },
            {
                "file": "VARA_EN_388_VER1.pdf",
                "title": "Guidance on Marketing of Virtual Assets",
                "effective_date": "2024-08-31",
            },
            {
                "file": "VARA_EN_516_VER1.pdf",
                "title": "Guidance on Virtual Asset Issuance",
                "effective_date": "2026-04-09",
            },
            {
                "file": "VARA_EN_215_VER20250519.pdf",
                "title": "Advisory Services Rulebook",
                "effective_date": "2025-05-19",
            },
            {
                "file": "VARA_EN_226_VER20250519.pdf",
                "title": "Broker-Dealer Services Rulebook",
                "effective_date": "2025-05-19",
            },
            {
                "file": "VARA_EN_243_VER20250519.pdf",
                "title": "Custody Services Rulebook",
                "effective_date": "2025-05-19",
            },
        ],
    },
}


def validate_config() -> None:
    """
    Fail fast at startup if the required API keys are missing.
    """
    if not LLM_API_KEY:
        raise ValueError(
            "LLM_API_KEY is not set. Copy .env.example to .env and add your Groq API key."
        )
    if not COHERE_API_KEY:
        raise ValueError(
            "COHERE_API_KEY is not set. Copy .env.example to .env and add your Cohere API key."
        )