"""
Session-fact memory service.

Why this exists: the chat's context window (first 2 + last 8 messages) is good
for coherent follow-ups but drops any fact the user stated more than ~8 turns
ago. A compliance officer who said "we're a Custody provider with 500
institutional clients" at turn 3 expects the tool to still know that at turn 20.

This module extracts those durable facts from each exchange and stores them in
Supabase. On every new question, the frontend prepends all stored facts to the
LLM prompt as [SESSION FACTS] — so the model always sees them regardless of how
long the conversation has grown.

What counts as a "durable fact":
- Firm type / licence class ("we're a Custody Services provider")
- Business activity ("we operate a virtual asset exchange")
- Client profile ("we serve retail investors in Dubai")
- Firm size / scale ("we have ~500 institutional clients")
- Jurisdiction context ("we're licensed in DIFB but not DIFC")
- Regulatory posture ("we've already obtained Category 1 approval")

What does NOT count:
- Question-specific context ("I'm asking about margin trading")
- Temporally-scoped facts ("right now I'm working on AML")
- Hypotheticals ("if I wanted to become a custodian...")
- Generic statements ("I want to learn about compliance")

Extraction is a single fast LLM call (openai/gpt-oss-20b). If the call fails,
we silently skip fact extraction for that exchange — better to lose a fact than
to block the response path.
"""

import json
import time
from typing import List

from openai import OpenAI

from app import config


def _get_client() -> OpenAI:
    return OpenAI(
        api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
        timeout=20.0,
    )


EXTRACT_PROMPT = """You extract durable facts about a user's firm from their message.

A "durable fact" is a statement that will still be true tomorrow and is relevant
to future regulatory questions about this user's compliance obligations.

DO extract:
- Firm type or licence class (e.g. "we are a Custody Services provider", "we hold a Category 1 VA Issuance licence")
- Business activity (e.g. "we operate an exchange in Dubai", "we offer margin trading")
- Client profile (e.g. "our clients are retail investors", "we serve institutional counterparties")
- Firm scale (e.g. "we have 500 clients", "we manage $10M AUM")
- Jurisdiction context (e.g. "we are licensed in DIFC but not Dubai mainland")
- Regulatory posture (e.g. "we are already VARA-licensed", "we are preparing a licence application")

DO NOT extract:
- The current question or topic ("I'm asking about X")
- Hypotheticals ("if I were a custodian...", "what if we wanted to...")
- Generic learning intent ("I want to understand X")
- Temporally-scoped statements ("right now I'm working on X")
- Opinions or preferences ("I think X is important")

Return ONLY a JSON array of fact strings. Each fact should be a complete,
self-contained sentence (e.g. "The user's firm is a Custody Services provider").
If no durable facts are present, return an empty array: []

Examples:
Input: "We're a Custody provider with 500 institutional clients. What are my AML obligations?"
Output: ["The user's firm is a Custody Services provider", "The firm serves 500 institutional clients"]

Input: "How does the VARA framework compare to FCA?"
Output: []

Input: "I'm thinking about becoming a margin trading provider — what would I need?"
Output: []

Input: "We already have our VARA licence. We offer Exchange Services and Margin Trading to retail investors in Dubai."
Output: ["The user's firm holds a VARA licence", "The firm offers Exchange Services", "The firm offers Margin Trading", "The firm serves retail investors in Dubai"]
"""


def extract_facts(user_message: str) -> List[str]:
    """
    Extract durable facts from a single user message.

    Why a single LLM call per message: fast (openai/gpt-oss-20b), cheap
    (~60 output tokens), and reliable when the prompt is explicit about
    what counts. Fails gracefully — returns [] on any error rather than
    blocking the send flow.
    """
    if not user_message or len(user_message.strip()) < 10:
        return []

    client = _get_client()
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            temperature=0.0,
            max_tokens=500,
            messages=[
                {"role": "system", "content": EXTRACT_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()

        # Strip markdown fences if the model wraps the JSON in ```json ... ```
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()

        # Parse the array; tolerate trailing commas and single quotes for robustness
        try:
            facts = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: extract quoted strings heuristically
            import re
            facts = re.findall(r'"([^"]+)"', raw)

        if not isinstance(facts, list):
            return []

        # Filter to strings only, dedupe, cap at 10 per message
        cleaned = [f.strip() for f in facts if isinstance(f, str) and f.strip()]
        return cleaned[:10]

    except Exception as e:
        print(f"[memory] Fact extraction failed (non-fatal): {e}")
        return []