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