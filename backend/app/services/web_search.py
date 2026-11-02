from typing import List, Dict, Any
from tavily import TavilyClient
from app import config

def search_web(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Query Tavily for the given question and return results formatted
    to match the structure our LLM and frontend expect.
    """
    if not config.TAVILY_API_KEY:
        print("[web_search] TAVILY_API_KEY not set. Skipping web search.")
        return []

    try:
        # Initialize client only when needed
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        
        # 'basic' search depth costs 1 credit and is sufficient for POC.
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=False # We want the LLM to synthesize, not Tavily's own answer
        )

        results = []
        for i, res in enumerate(response.get("results", [])):
            results.append({
                "text": res.get("content", ""),
                "page": i + 1,  # Web results don't have page numbers, use index
                "section": "Web Search Result",
                "document": res.get("title", "Web Source"),
                "source_url": res.get("url", ""),
                "distance": 0.0 # Internal score, not used for web results
            })
        return results

    except Exception as e:
        print(f"[web_search] Tavily search failed: {e}")
        return []
