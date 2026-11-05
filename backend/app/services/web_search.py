from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from tavily import TavilyClient

from app import config


def _extract_host(url: str) -> str:
    """Return the bare hostname of a URL (no 'www.', no port). Empty on error."""
    if not url:
        return ""
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def _authority_tier(url: str) -> Optional[str]:
    """
    Classify a web source URL into 'primary', 'press', or None.
    'general' sources (blogs, LinkedIn, Medium, Instagram, help pages) are
    REJECTED entirely — this tool must not cite them as regulatory sources.
    The lists live in config.TRUSTED_DOMAINS — extend there, not here.
    """
    host = _extract_host(url)
    if not host:
        return None

    for domain in config.TRUSTED_DOMAINS.get("primary", []):
        if host == domain or host.endswith("." + domain):
            return "primary"
    for domain in config.TRUSTED_DOMAINS.get("press", []):
        if host == domain or host.endswith("." + domain):
            return "press"
    return None


def _match_jurisdiction_keywords(query: str) -> List[str]:
    """
    Return the domains to restrict the search to, based on any country /
    regulator keyword appearing in the query. Empty list means no restriction
    (falls back to open search filtered by authority tier).
    """
    lower = query.lower()
    domains: List[str] = []
    for key, mapped in config.JURISDICTION_DOMAIN_MAP.items():
        # Match keyword as a whole word so "us" doesn't fire on "customer"
        import re as _re
        if _re.search(rf"\b{_re.escape(key)}\b", lower):
            for d in mapped:
                if d not in domains:
                    domains.append(d)
    return domains


def _format_results(raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert Tavily results to our chunk shape, dropping untrusted sources."""
    out: List[Dict[str, Any]] = []
    for res in raw_results:
        url = res.get("url", "")
        tier = _authority_tier(url)
        if tier is None:
            # Untrusted source — drop silently. This is the fix for the
            # LinkedIn/Medium/Instagram results that polluted earlier demos.
            continue
        out.append({
            "text": res.get("content", ""),
            "page": len(out) + 1,
            "section": "Web Search Result",
            "document": res.get("title", "Web Source"),
            "source_url": url,
            "distance": 0.0,
            "authority_tier": tier,
        })
    return out


def search_web(query: str, max_results: int = None) -> List[Dict[str, Any]]:
    """
    Search the web via Tavily, restricted to trusted regulatory / press domains.

    Two-pass strategy:
      Pass 1 — if the query mentions a specific jurisdiction (Nigeria, UK, FCA,
               SEC, etc.), restrict Tavily to that jurisdiction's domains via
               include_domains. Most authoritative results, narrowest scope.
      Pass 2 — if Pass 1 returns nothing, run an open search with no domain
               restriction, but DROP any result whose domain isn't in
               TRUSTED_DOMAINS (primary or press).

    If both passes yield nothing trusted, return []. The caller (routes.py)
    will then have no chunks and the LLM will honestly refuse — which is
    preferable to citing a blog.
    """
    if not config.TAVILY_API_KEY:
        print("[web_search] TAVILY_API_KEY not set. Skipping web search.")
        return []

    if max_results is None:
        max_results = config.WEB_SEARCH_MAX_RESULTS

    try:
        client = TavilyClient(api_key=config.TAVILY_API_KEY)

        # --- Pass 1: restricted by jurisdiction keyword, if any -------------
        jurisdiction_domains = _match_jurisdiction_keywords(query)
        if jurisdiction_domains:
            print(f"[web_search] Pass 1 — restricted to {len(jurisdiction_domains)} trusted domains for detected jurisdiction.")
            try:
                restricted = client.search(
                    query=query,
                    search_depth=config.WEB_SEARCH_DEPTH,
                    max_results=max_results,
                    include_answer=False,
                    include_domains=jurisdiction_domains,
                )
                formatted = _format_results(restricted.get("results", []))
                if formatted:
                    print(f"[web_search] Pass 1 returned {len(formatted)} trusted source(s).")
                    return formatted
                print("[web_search] Pass 1 empty; falling through to Pass 2.")
            except Exception as exc:
                print(f"[web_search] Pass 1 failed: {exc}")

        # --- Pass 2: open search, filtered by authority tier ----------------
        print("[web_search] Pass 2 — open search, filtering to trusted domains.")
        open_result = client.search(
            query=query,
            search_depth=config.WEB_SEARCH_DEPTH,
            max_results=max_results * 3,  # pull extra so we have more to filter from
            include_answer=False,
        )
        formatted = _format_results(open_result.get("results", []))
        if formatted:
            print(f"[web_search] Pass 2 returned {len(formatted)} trusted source(s).")
            return formatted[:max_results]

        print("[web_search] No trusted sources found for this query.")
        return []

    except Exception as e:
        print(f"[web_search] Tavily search failed: {e}")
        return []