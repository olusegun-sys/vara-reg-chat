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

# --- LLM Provider Settings (OpenAI-compatible) ---
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b").strip()
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))

# --- Embeddings (Cohere) ---
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "").strip()
EMBEDDING_MODEL = "embed-english-v3.0"

# --- Web Search Fallback (Tavily) ---
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()

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
TOP_K_RESULTS = 8

# ============================================================================
# --- Fallback & Authority Policy ---
# ============================================================================

# FAISS confidence threshold. 1.15 sits in the gap between good (~0.5-0.9)
# and junk (~1.3+) matches on this corpus.
LOW_CONFIDENCE_DISTANCE = 1.15

# If the user's question contains one of these tokens (\b-anchored), route
# directly to web search. Add a regulator: append to the list.
OUT_OF_SCOPE_JURISDICTION_TOKENS = [
    "fca", "sec", "mas", "finma", "cbn", "uk", "us", "usa",
    "singapore", "nigeria", "bafin", "cma", "asic",
]

# If the LLM's answer contains one of these phrases (case-insensitive), treat
# as a refusal and retry once with web search.
REFUSAL_PATTERNS = [
    "i don't have that information",
    "i don't have that in",
    "not mentioned in the retrieved",
    "not in the retrieved excerpts",
    "not contained in the provided",
    "the provided documents do not",
    "the retrieved excerpts do not",
    "i cannot answer this based on",
]

# Tavily tuning.
WEB_SEARCH_DEPTH = "advanced"
WEB_SEARCH_MAX_RESULTS = 5

# ============================================================================
# --- Web Search Authority Filtering ---
# The web fallback will ONLY return results from domains in this list. Any
# result from a blog, aggregator, social media, or unknown site is dropped
# silently. This is deliberate: a compliance tool must cite regulators and
# established press, not LinkedIn posts.
# ============================================================================

TRUSTED_DOMAINS = {
    # Primary regulators / official government sources
    "primary": [
        # UAE / Dubai
        "vara.ae",
        "mof.gov.ae",
        "centralbank.ae",
        # EU
        "eur-lex.europa.eu",
        "europa.eu",
        # UK
        "fca.org.uk",
        "gov.uk",
        "hmrc.gov.uk",
        "bankofengland.co.uk",
        # US
        "sec.gov",
        "irs.gov",
        "federalreserve.gov",
        "treasury.gov",
        "cftc.gov",
        # Singapore
        "mas.gov.sg",
        # Switzerland
        "finma.ch",
        # Nigeria
        "firs.gov.ng",
        "nrs.gov.ng",
        "cbn.gov.ng",
        "sec.gov.ng",
        # Germany
        "bafin.de",
        # Australia
        "asic.gov.au",
        # Saudi
        "cma.gov.sa",
    ],
    # Established financial / legal press
    "press": [
        "reuters.com",
        "ft.com",
        "bloomberg.com",
        "wsj.com",
        "economist.com",
        "lawfaremedia.org",
        "businessday.ng",
        "punchng.com",
        "premiumtimesng.com",
        "guardian.ng",
        "thecable.ng",
    ],
}

# Maps a country/regulator keyword found in the question to the domains Tavily
# should restrict its search to. Used as Pass 1 of the two-pass strategy.
# Extend freely — no code changes needed.
JURISDICTION_DOMAIN_MAP = {
    "nigeria": [
        "firs.gov.ng", "nrs.gov.ng", "cbn.gov.ng", "sec.gov.ng",
        "businessday.ng", "punchng.com", "premiumtimesng.com",
        "guardian.ng", "thecable.ng",
    ],
    "cbn": ["cbn.gov.ng", "businessday.ng", "punchng.com"],
    "uk": [
        "fca.org.uk", "gov.uk", "hmrc.gov.uk", "bankofengland.co.uk",
        "reuters.com", "ft.com",
    ],
    "fca": ["fca.org.uk", "gov.uk", "reuters.com", "ft.com"],
    "us": ["sec.gov", "irs.gov", "federalreserve.gov", "cftc.gov", "reuters.com", "bloomberg.com"],
    "sec": ["sec.gov", "reuters.com", "bloomberg.com"],
    "singapore": ["mas.gov.sg", "reuters.com", "bloomberg.com"],
    "mas": ["mas.gov.sg", "reuters.com"],
    "switzerland": ["finma.ch", "reuters.com"],
    "finma": ["finma.ch", "reuters.com"],
    "germany": ["bafin.de", "reuters.com"],
    "bafin": ["bafin.de", "reuters.com"],
    "australia": ["asic.gov.au", "reuters.com"],
    "asic": ["asic.gov.au", "reuters.com"],
    "saudi": ["cma.gov.sa", "reuters.com"],
    "eu": ["eur-lex.europa.eu", "europa.eu", "reuters.com"],
}

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
            {
                "file": "VARA_EN_18_VER992_2.pdf",
                "title": "Virtual Assets and Related Activities Regulations 2023",
                "effective_date": "2023-02-07",
                "source_url": "https://rulebooks.vara.ae/sites/default/files/en_net_file_store/VARA_EN_18_VER992_2.pdf",
                "document_type": "regulation",
            },
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
    "EU": {
        "regulator": "European Union",
        "name": "European Union — Artificial Intelligence",
        "documents": [
            {
                "file": "EU_AI_Act_Regulation_2024_1689.pdf",
                "title": "Regulation (EU) 2024/1689 — EU Artificial Intelligence Act",
                "effective_date": "2026-08-02",
                "source_url": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
                "document_type": "regulation",
            },
            {
                "file": "EU_AI_Act_Omnibus_2026_1744.pdf",
                "title": "Regulation (EU) 2026/1744 — Digital Omnibus on AI (amending the EU AI Act)",
                "effective_date": "2026-07-27",
                "source_url": "https://eur-lex.europa.eu/eli/reg/2026/1744/oj",
                "document_type": "amendment",
            },
        ],
    },
}


def validate_config() -> None:
    if not LLM_API_KEY:
        raise ValueError(
            "LLM_API_KEY is not set. Copy .env.example to .env and add your Groq API key."
        )
    if not COHERE_API_KEY:
        raise ValueError(
            "COHERE_API_KEY is not set. Copy .env.example to .env and add your Cohere API key."
        )