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
# Groq, DeepSeek, OpenAI, Together, etc. all speak this format.
# Switching providers = change these three env vars, code stays identical.
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))  # 0.1 = focused, less creative
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))    # response length cap

# --- Embeddings ---
# Gemini is used for cloud embeddings to eliminate PyTorch RAM overhead.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EMBEDDING_MODEL = "models/gemini-embedding-001"

# --- Vector Store (FAISS) ---
# FAISS stores the vector index in a binary file; metadata lives in a JSON sidecar.
FAISS_INDEX_PATH = os.getenv(
    "FAISS_INDEX_PATH",
    str(BASE_DIR / "faiss_index" / "index.faiss"),
)
FAISS_METADATA_PATH = os.getenv(
    "FAISS_METADATA_PATH",
    str(BASE_DIR / "faiss_index" / "metadata.json"),
)

# --- Chunking & Retrieval ---
# 800 tokens per chunk, 150 token overlap so context isn't cut off mid-sentence.
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "7"))  # return 7 most relevant chunks

# --- Jurisdiction Registry ---
# This is the heart of multi-jurisdiction design.
# Each entry maps a jurisdiction code to its regulator, name, and documents.
# The ingestion script and retrieval filter both read from this dict.
JURISDICTIONS = {
    "AE-Dubai": {
        "regulator": "VARA",
        "name": "Dubai Virtual Assets Regulatory Authority",
        "documents": [
            {
                "file": "vara_compliance_risk_rulebook.pdf",
                "title": "Compliance and Risk Management Rulebook",
                "effective_date": "2025-05-19",
            },
            {
                "file": "vara_company_rulebook.pdf",
                "title": "Company Rulebook",
                "effective_date": "2025-05-19",
            },
            {
                "file": "vara_technology_rulebook.pdf",
                "title": "Technology and Information Rulebook",
                "effective_date": "2025-05-19",
            },
            {
                "file": "vara_market_conduct_rulebook.pdf",
                "title": "Market Conduct Rulebook",
                "effective_date": "2025-05-19",
            },
        ],
    },
    # Example future entry — do not uncomment until you have the PDF:
    # "NG": {
    #     "regulator": "CBN",
    #     "name": "Central Bank of Nigeria",
    #     "documents": [
    #         {
    #             "file": "cbn_risk_management_rulebook.pdf",
    #             "title": "CBN Risk Management Guidelines",
    #             "effective_date": "2026-01-01",
    #         }
    #     ],
    # },
}


def validate_config() -> None:
    """
    Fail fast at startup if the required API keys are missing.
    Why: better to crash at startup with a clear message than to fail
    mysteriously on the first chat request.
    """
    if not LLM_API_KEY:
        raise ValueError(
            "LLM_API_KEY is not set. Copy .env.example to .env and add your Groq API key."
        )
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your Gemini API key."
        )