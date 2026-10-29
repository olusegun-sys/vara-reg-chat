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
            # STATE AS OF 2026-10-29 EVENING: 17 documents configured.
            # FAISS index on disk: 1,081 vectors (11 docs) + ~500 new (6 docs
            # being ingested in this run) = expected ~1,500-1,800 total.
            #
            # This list is the SOURCE OF TRUTH for a --reset rebuild.
            # New ingestions use scripts/ingest.py which skips titles already
            # present in metadata.json, so re-running is safe (no duplicates).
            # ================================================================

            # --- Compulsory Rulebooks (4/4) ---
            {
                "file": "vara_compliance_risk_rulebook.txt",
                "title": "Compliance and Risk Management Rulebook",
                "effective_date": "2025-05-19",
                "source_url": "https://rulebooks.vara.ae/index.php/rulebook/compliance-and-risk-management-rulebook",
                "document_type": "rulebook",
            },
            {
                "file": "vara_company_rulebook.txt",
                "title": "Company Rulebook",
                "effective_date": "2025-05-19",
                "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_36_VER20250519.pdf",
                "document_type": "rulebook",
            },
            {
                "file": "vara_technology_rulebook.txt",
                "title": "Technology and Information Rulebook",
                "effective_date": "2025-05-19",
                "source_url": "https://rulebooks.vara.ae/index.php/rulebook/technology-and-information-rulebook",
                "document_type": "rulebook",
            },
            {
                "file": "vara_market_conduct_rulebook.txt",
                "title": "Market Conduct Rulebook",
                "effective_date": "2025-05-19",
                "source_url": "https://rulebooks.vara.ae/index.php/rulebook/market-conduct-rulebook",
                "document_type": "rulebook",
            },

            # --- VA Activity Rulebooks (7/9, already ingested) ---
            {
                "file": "VARA_EN_258_VER20260331.pdf",
                "title": "Exchange Services Rulebook",
                "effective_date": "2026-03-31",
                "source_url": "https://rulebooks.vara.ae/index.php/rulebook/exchange-services-rulebook",
                "document_type": "rulebook",
            },
            {
                "file": "VARA_EN_279_VER20250519.pdf",
                "title": "Lending and Borrowing Services Rulebook",
                "effective_date": "2025-05-19",
                "source_url": "https://rulebooks.vara.ae/index.php/rulebook/lending-and-borrowing-services-rulebook",
                "document_type": "rulebook",
            },
            {
                "file": "VARA_EN_215_VER20250519.pdf",
                "title": "Advisory Services Rulebook",
                "effective_date": "2025-05-19",
                "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_215_VER20250519.pdf",
                "document_type": "rulebook",
            },
            {
                "file": "VARA_EN_226_VER20250519.pdf",
                "title": "Broker-Dealer Services Rulebook",
                "effective_date": "2025-05-19",
                "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_226_VER20250519.pdf",
                "document_type": "rulebook",
            },
            {
                "file": "VARA_EN_243_VER20250519.pdf",
                "title": "Custody Services Rulebook",
                "effective_date": "2025-05-19",
                "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_243_VER20250519.pdf",
                "document_type": "rulebook",
            },

            # --- Guidance Documents (2/2, already ingested) ---
            {
                "file": "VARA_EN_388_VER1.pdf",
                "title": "Guidance on Marketing of Virtual Assets",
                "effective_date": "2024-08-31",
                "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_388_VER1.pdf",
                "document_type": "guidance",
            },
            {
                "file": "VARA_EN_516_VER1.pdf",
                "title": "Guidance on Virtual Asset Issuance",
                "effective_date": "2026-04-09",
                "source_url": "https://rulebooks.vara.ae/index.php/rulebook/virtual-asset-issuance-rulebook",
                "document_type": "guidance",
            },

            # ================================================================
            # NEW (2026-10-29 EVENING): 6 VARA framework documents
            # These complete the framework layer: Laws, Cabinet Decisions,
            # master Regulations, plus the last 2 VA Activity rulebooks.
            # ================================================================

            # --- VA Activity Rulebooks (2 more, completing 9/9) ---
            {
                "file": "VARA_EN_317_VER20250519.pdf",
                "title": "VA Management and Investment Services Rulebook",
                "effective_date": "2025-05-19",
                "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_317_VER20250519.pdf",
                "document_type": "rulebook",
            },
            {
                "file": "VARA_EN_347_VER20250519.pdf",
                "title": "VA Transfer and Settlement Services Rulebook",
                "effective_date": "2025-05-19",
                "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_347_VER20250519.pdf",
                "document_type": "rulebook",
            },

            # --- Master Regulation (foundation of the whole framework) ---
            {
                "file": "VARA_EN_18_VER992_2.pdf",
                "title": "Virtual Assets and Related Activities Regulations 2023",
                "effective_date": "2023-02-07",
                "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_18_VER992_2.pdf",
                "document_type": "regulation",
            },

            # --- Laws & Cabinet Decisions (the legal framework above VARA) ---
            {
                "file": "VARA_EN_338_VER1.pdf",
                "title": "Law No. (4) of 2022 Regulating Virtual Assets in the Emirate of Dubai",
                "effective_date": "2022-03-11",
                "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_338_VER1.pdf",
                "document_type": "law",
            },
            {
                "file": "VARA_EN_339_VER1.pdf",
                "title": "Cabinet Decision No. 111/2022 on the Regulation of Virtual Assets and Their Service Providers",
                "effective_date": "2022-12-12",
                "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_339_VER1.pdf",
                "document_type": "cabinet_decision",
            },
            {
                "file": "VARA_EN_340_VER1.pdf",
                "title": "Cabinet Decision No. 112/2022 on Delegating Certain Competencies related to the Regulation of Virtual Assets",
                "effective_date": "2022-12-12",
                "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_340_VER1.pdf",
                "document_type": "cabinet_decision",
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