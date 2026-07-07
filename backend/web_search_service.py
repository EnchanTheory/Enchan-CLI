def perform_web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Execute a web search using DuckDuckGo and return formatted results.
    """
    try:
        from ddgs import DDGS
    except ModuleNotFoundError:
        return [{"error": "web_search requires the 'ddgs' package. Run the installer/update so requirements.txt is installed."}]

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
