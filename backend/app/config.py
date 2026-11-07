"""
Central configuration for the Regulatory Knowledge Base Chat.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# --- LLM Provider Settings (Primary: Groq) ---
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b").strip()
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1500"))

# --- LLM Provider Settings (Backup 1: OpenRouter) ---
BACKUP_LLM_API_KEY = os.getenv("BACKUP_LLM_API_KEY", "").strip()
BACKUP_LLM_BASE_URL = os.getenv("BACKUP_LLM_BASE_URL", "https://openrouter.ai/api/v1").strip()
BACKUP_LLM_MODEL = os.getenv("BACKUP_LLM_MODEL", "meta-llama/llama-3-70b-instruct:free").strip()

# --- LLM Provider Settings (Backup 2: Google Gemini) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()

# --- Embeddings (Cohere) ---
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "").strip()
EMBEDDING_MODEL = "embed-english-v3.0"

# --- Web Search Fallback (Tier 1: Tavily, Tier 2: Serper) ---
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()

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
TOP_K_RESULTS = 5

# --- Web Fallback Configuration ---
WEB_SEARCH_DEPTH = "advanced"
WEB_SEARCH_MAX_RESULTS = 3
LOW_CONFIDENCE_DISTANCE = 1.15

# REMOVED "us" and "uk". 
# Why: Questions like "A US bank..." were incorrectly triggering web search 
# for EU questions, causing false refusals.
OUT_OF_SCOPE_JURISDICTION_TOKENS = [
    "fca", "sec", "mas", "finma", "cbn", "singapore", "nigeria"
]

TRUSTED_DOMAINS = [
    "eur-lex.europa.eu", "fca.org.uk", "sec.gov", "gov.uk", "mas.gov.sg",
    "finma.ch", "cbn.gov.ng", "vara.ae", "reuters.com", "ft.com", "bloomberg.com"
]

# --- Jurisdiction Registry ---
JURISDICTIONS = {
    "AE-Dubai": {
        "regulator": "VARA",
        "name": "Dubai Virtual Assets Regulatory Authority",
        "documents": [
            # Compulsory Rulebooks (4)
            {"file": "vara_compliance_risk_rulebook.txt", "title": "Compliance and Risk Management Rulebook", "effective_date": "2025-05-19", "source_url": "https://rulebooks.vara.ae/index.php/rulebook/compliance-and-risk-management-rulebook", "document_type": "rulebook"},
            {"file": "vara_company_rulebook.txt", "title": "Company Rulebook", "effective_date": "2025-05-19", "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_36_VER20250519.pdf", "document_type": "rulebook"},
            {"file": "vara_technology_rulebook.txt", "title": "Technology and Information Rulebook", "effective_date": "2025-05-19", "source_url": "https://rulebooks.vara.ae/index.php/rulebook/technology-and-information-rulebook", "document_type": "rulebook"},
            {"file": "vara_market_conduct_rulebook.txt", "title": "Market Conduct Rulebook", "effective_date": "2025-05-19", "source_url": "https://rulebooks.vara.ae/index.php/rulebook/market-conduct-rulebook", "document_type": "rulebook"},
            # VA Activity Rulebooks (9)
            {"file": "VARA_EN_258_VER20260331.pdf", "title": "Exchange Services Rulebook", "effective_date": "2026-03-31", "source_url": "https://rulebooks.vara.ae/index.php/rulebook/exchange-services-rulebook", "document_type": "rulebook"},
            {"file": "VARA_EN_279_VER20250519.pdf", "title": "Lending and Borrowing Services Rulebook", "effective_date": "2025-05-19", "source_url": "https://rulebooks.vara.ae/index.php/rulebook/lending-and-borrowing-services-rulebook", "document_type": "rulebook"},
            {"file": "VARA_EN_215_VER20250519.pdf", "title": "Advisory Services Rulebook", "effective_date": "2025-05-19", "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_215_VER20250519.pdf", "document_type": "rulebook"},
            {"file": "VARA_EN_226_VER20250519.pdf", "title": "Broker-Dealer Services Rulebook", "effective_date": "2025-05-19", "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_226_VER20250519.pdf", "document_type": "rulebook"},
            {"file": "VARA_EN_243_VER20250519.pdf", "title": "Custody Services Rulebook", "effective_date": "2025-05-19", "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_243_VER20250519.pdf", "document_type": "rulebook"},
            {"file": "VARA_EN_317_VER20250519.pdf", "title": "VA Management and Investment Services Rulebook", "effective_date": "2025-05-19", "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_317_VER20250519.pdf", "document_type": "rulebook"},
            {"file": "VARA_EN_347_VER20250519.pdf", "title": "VA Transfer and Settlement Services Rulebook", "effective_date": "2025-05-19", "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_347_VER20250519.pdf", "document_type": "rulebook"},
            # Guidance (2)
            {"file": "VARA_EN_388_VER1.pdf", "title": "Guidance on Marketing of Virtual Assets", "effective_date": "2024-08-31", "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_388_VER1.pdf", "document_type": "guidance"},
            {"file": "VARA_EN_516_VER1.pdf", "title": "Guidance on Virtual Asset Issuance", "effective_date": "2026-04-09", "source_url": "https://rulebooks.vara.ae/index.php/rulebook/virtual-asset-issuance-rulebook", "document_type": "guidance"},
            # Framework Documents (4)
            {"file": "VARA_EN_18_VER992_2.pdf", "title": "Virtual Assets and Related Activities Regulations 2023", "effective_date": "2023-02-07", "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_18_VER992_2.pdf", "document_type": "regulation"},
            {"file": "VARA_EN_338_VER1.pdf", "title": "Law No. (4) of 2022 Regulating Virtual Assets in the Emirate of Dubai", "effective_date": "2022-03-11", "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_338_VER1.pdf", "document_type": "law"},
            {"file": "VARA_EN_339_VER1.pdf", "title": "Cabinet Decision No. 111/2022 on the Regulation of Virtual Assets and Their Service Providers", "effective_date": "2022-12-12", "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_339_VER1.pdf", "document_type": "cabinet_decision"},
            {"file": "VARA_EN_340_VER1.pdf", "title": "Cabinet Decision No. 112/2022 on Delegating Certain Competencies related to the Regulation of Virtual Assets", "effective_date": "2022-12-12", "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_340_VER1.pdf", "document_type": "cabinet_decision"},
        ],
    },
    "EU": {
        "regulator": "European Union",
        "name": "European Union — Artificial Intelligence",
        "documents": [
            {"file": "EU_AI_Act_Regulation_2024_1689.pdf", "title": "Regulation (EU) 2024/1689 — EU Artificial Intelligence Act", "effective_date": "2026-08-02", "source_url": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj", "document_type": "regulation"},
            {"file": "EU_AI_Act_Omnibus_2026_1744.pdf", "title": "Regulation (EU) 2026/1744 — Digital Omnibus on AI (amending the EU AI Act)", "effective_date": "2026-07-27", "source_url": "https://eur-lex.europa.eu/eli/reg/2026/1744/oj", "document_type": "amendment"},
        ],
    },
}


def validate_config() -> None:
    if not LLM_API_KEY:
        raise ValueError("LLM_API_KEY is not set.")
    if not COHERE_API_KEY:
        raise ValueError("COHERE_API_KEY is not set.")