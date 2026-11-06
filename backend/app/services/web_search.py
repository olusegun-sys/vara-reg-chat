import json
import httpx
from typing import List, Dict, Any
from tavily import TavilyClient
from app import config

def _is_trusted(url: str) -> bool:
    """Check if the URL belongs to a known trusted domain."""
    if not url: return False
    return any(domain in url.lower() for domain in config.TRUSTED_DOMAINS)

def _get_tier(url: str) -> str:
    """Classify the source as primary or press."""
    if not url: return "general"
    primary = ["eur-lex", "fca.org.uk", "sec.gov", "gov.uk", "mas.gov.sg", "finma.ch", "cbn.gov.ng", "vara.ae"]
    press = ["reuters.com", "ft.com", "bloomberg.com"]
    if any(d in url.lower() for d in primary): return "primary"
    if any(d in url.lower() for d in press): return "press"
    return "general"

def _search_tavily(query: str) -> List[Dict[str, Any]]:
    if not config.TAVILY_API_KEY: return []
    try:
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        response = client.search(query=query, search_depth=config.WEB_SEARCH_DEPTH, max_results=5)
        
        results = []
        for i, res in enumerate(response.get("results", [])):
            url = res.get("url", "")
            if not _is_trusted(url): continue
            
            results.append({
                "text": res.get("content", ""),
                "page": i + 1,
                "section": "Web Search Result",
                "document": res.get("title", "Web Source"),
                "source_url": url,
                "authority_tier": _get_tier(url),
                "distance": 0.0
            })
        return results
    except Exception as e:
        print(f"[web_search] Tavily failed: {e}")
        return []

def _search_serper(query: str) -> List[Dict[str, Any]]:
    if not config.SERPER_API_KEY: return []
    try:
        url = "https://google.serper.dev/search"
        payload = json.dumps({"q": query, "num": 5})
        headers = {
            'X-API-KEY': config.SERPER_API_KEY,
            'Content-Type': 'application/json'
        }
        response = httpx.post(url, headers=headers, data=payload, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for i, res in enumerate(data.get("organic", [])):
            link = res.get("link", "")
            if not _is_trusted(link): continue
            
            # Serper doesn't return full page text, just a snippet.
            # We combine title + snippet so the LLM has enough context.
            text = res.get("snippet", "")
            title = res.get("title", "Web Source")
            
            results.append({
                "text": f"{title}\n{text}",
                "page": i + 1,
                "section": "Web Search Result",
                "document": title,
                "source_url": link,
                "authority_tier": _get_tier(link),
                "distance": 0.0
            })
        return results
    except Exception as e:
        print(f"[web_search] Serper failed: {e}")
        return []

def search_web(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Try Tavily first. If it returns nothing (e.g. misses obscure PDFs), try Serper (Google).
    """
    print(f"[web_search] Searching for: {query}")
    
    # 1. Try Tavily (great for standard web content)
    results = _search_tavily(query)
    if results:
        print(f"[web_search] Tavily found {len(results)} results.")
        return results[:max_results]
        
    # 2. Fallback to Serper (Google) for obscure PDFs and news
    print("[web_search] Tavily found nothing. Falling back to Serper (Google)...")
    results = _search_serper(query)
    if results:
        print(f"[web_search] Serper found {len(results)} results.")
        return results[:max_results]
        
    print("[web_search] Both Tavily and Serper returned no trusted results.")
    return []