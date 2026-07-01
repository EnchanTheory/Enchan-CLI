from ddgs import DDGS

def perform_web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Execute a web search using DuckDuckGo and return formatted results.
    """
    results = []
    try:
        with DDGS() as ddgs:
            # Use text search mode
            search_results = ddgs.text(query, max_results=max_results)
            for res in search_results:
                results.append({
                    "title": res.get("title"),
                    "url": res.get("href"),
                    "snippet": res.get("body"),
                })
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]
    return results
