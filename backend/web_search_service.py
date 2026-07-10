AD_URL_MARKERS = (
    "bing.com/aclick",
    "bing.com/fd/ls/",
    "duckduckgo.com/y.js",
    "google.com/aclk",
    "googleadservices.com",
    "googlesyndication.com",
    "doubleclick.net",
    "/pagead/",
    "/aclk?",
    "/aclick?",
)

AD_TITLE_MARKERS = (
    "【広告】",
    "[ad]",
    "(ad)",
    " sponsored",
    "sponsored ",
    "anzeige",
    "annonce",
    "publicidad",
    "광고",
    "广告",
)


def _search_result_url(res: dict) -> str:
    return str(res.get("href") or res.get("url") or "")


def _is_ad_result(res: dict) -> bool:
    """Return True when a DDGS result looks like a paid ad.

    Prefer locale-independent ad redirect URLs. Visible ad labels are localized and
    can be missing, so title markers are only a secondary best-effort signal.
    """
    url = _search_result_url(res).lower()
    if any(marker in url for marker in AD_URL_MARKERS):
        return True

    title = str(res.get("title") or "").strip().lower()
    return any(marker in title for marker in AD_TITLE_MARKERS)


def _format_search_result(res: dict) -> dict:
    return {
        "title": res.get("title"),
        "url": _search_result_url(res),
        "snippet": res.get("body"),
    }


def perform_web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Execute a web search using DuckDuckGo and return formatted, non-ad results.
    """
    try:
        from ddgs import DDGS
    except ModuleNotFoundError:
        return [{"error": "web_search requires the 'ddgs' package. Run the installer/update so requirements.txt is installed."}]

    results = []
    try:
        with DDGS() as ddgs:
            # Request extra results so filtering paid ad redirects still leaves a
            # full organic result set when enough organic results are available.
            search_limit = max(max_results * 2, max_results)
            search_results = ddgs.text(query, max_results=search_limit)
            for res in search_results:
                if _is_ad_result(res):
                    continue
                results.append(_format_search_result(res))
                if len(results) >= max_results:
                    break
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]
    return results
