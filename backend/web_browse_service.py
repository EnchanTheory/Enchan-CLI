import html
import ipaddress
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from html.parser import HTMLParser


DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_MAX_CHARS = 12000
MIN_READABLE_CHARS = 500
MAX_RESULTS_PER_DOMAIN = 2
DEFAULT_MAX_DEPTH = 1
MAX_LINKS_PER_PAGE = 80
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 EnchanCLI/1.0"
)

SEARCH_HOST_MARKERS = (
    "bing.com",
    "duckduckgo.com",
    "google.com",
    "search.yahoo.com",
    "search.yahoo.co.jp",
)

BLOCKED_LINK_MARKERS = (
    "/login",
    "/signin",
    "/signup",
    "/register",
    "/account",
    "/share",
    "facebook.com/sharer",
    "twitter.com/intent",
    "x.com/intent",
    "linkedin.com/share",
    "mailto:",
    "javascript:",
)


class _ReadableTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._chunks: list[str] = []
        self._title: list[str] = []
        self._in_title = False
        self._current_href: str | None = None
        self._anchor_chunks: list[str] = []
        self._links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "canvas", "iframe"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = True
        if tag == "a":
            href = dict(attrs).get("href")
            self._current_href = str(href).strip() if href else None
            self._anchor_chunks = []
        if tag in {"p", "br", "div", "section", "article", "header", "h1", "h2", "h3", "li", "tr"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if self._skip_depth:
            if tag in {"script", "style", "noscript", "svg", "canvas", "iframe"}:
                self._skip_depth -= 1
            return
        if tag == "title":
            self._in_title = False
        if tag == "a":
            if self._current_href:
                anchor_text = _normalize_text(" ".join(self._anchor_chunks))
                self._links.append((self._current_href, anchor_text))
            self._current_href = None
            self._anchor_chunks = []
        if tag in {"p", "div", "section", "article", "h1", "h2", "h3", "li", "tr"}:
            self._chunks.append("\n")

    def handle_data(self, data: str):
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self._title.append(text)
        if self._current_href:
            self._anchor_chunks.append(text)
        self._chunks.append(text)
        self._chunks.append(" ")

    def title(self) -> str:
        return _normalize_text(" ".join(self._title))

    def text(self) -> str:
        return _normalize_text("".join(self._chunks))

    def links(self) -> list[tuple[str, str]]:
        return self._links[:MAX_LINKS_PER_PAGE]


def _normalize_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _decode_response(raw: bytes, content_type: str) -> str:
    match = re.search(r"charset=([^;\s]+)", content_type or "", flags=re.I)
    encodings = [match.group(1)] if match else []
    encodings.extend(["utf-8", "cp932", "shift_jis", "euc_jp", "latin-1"])
    for encoding in encodings:
        try:
            return raw.decode(encoding, errors="replace")
        except LookupError:
            continue
    return raw.decode("utf-8", errors="replace")


def _normalized_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    cleaned = parsed._replace(fragment="")
    return urllib.parse.urlunparse(cleaned)


def _host(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.lower().split(":", 1)[0]


def _is_search_result_page(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower().split(":", 1)[0]
    if not any(host == marker or host.endswith("." + marker) for marker in SEARCH_HOST_MARKERS):
        return False
    path = parsed.path.lower()
    query = parsed.query.lower()
    return path in {"", "/", "/search", "/html", "/lite"} or "q=" in query or "query=" in query


def _is_public_discovered_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    host = parsed.hostname or ""
    if host.lower() == "localhost" or host.lower().endswith(".local"):
        return False
    try:
        address = ipaddress.ip_address(host)
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            return False
    except ValueError:
        pass
    lowered = url.lower()
    return not any(marker in lowered for marker in BLOCKED_LINK_MARKERS)


def _query_terms(query: str) -> set[str]:
    terms = re.findall(r"[a-z0-9_\-]{2,}|[ぁ-んァ-ヶ一-龠]{2,}", query.lower())
    stop = {"について", "教えて", "とは", "the", "and", "for", "what", "how", "latest", "today"}
    return {term for term in terms if term not in stop}


def _link_score(query: str, source_url: str, target_url: str, anchor_text: str) -> int:
    terms = _query_terms(query)
    haystack = f"{anchor_text} {urllib.parse.unquote(target_url)}".lower()
    score = sum(4 for term in terms if term in haystack)
    source_host = _host(source_url)
    target_host = _host(target_url)
    if source_host and target_host == source_host:
        score += 2
    path = urllib.parse.urlparse(target_url).path.lower()
    if any(marker in path for marker in ("/docs/", "/documentation/", "/guide/", "/article/", "/news/", "/blog/", "/press/", "/release/")):
        score += 2
    if anchor_text and 4 <= len(anchor_text) <= 140:
        score += 1
    if any(marker in path for marker in ("/tag/", "/category/", "/author/", "/archive/", "/privacy", "/terms")):
        score -= 3
    return score


def _rank_links(query: str, page: dict) -> list[dict]:
    source_url = str(page.get("url") or "")
    ranked: list[dict] = []
    seen: set[str] = set()
    for raw_url, anchor_text in page.get("links") or []:
        target = _normalized_url(urllib.parse.urljoin(source_url, raw_url))
        if target in seen or target == source_url:
            continue
        seen.add(target)
        if not _is_public_discovered_url(target) or _is_search_result_page(target):
            continue
        ranked.append({
            "url": target,
            "anchor_text": anchor_text,
            "score": _link_score(query, source_url, target, anchor_text),
        })
    ranked.sort(key=lambda item: (item["score"], len(item["anchor_text"])), reverse=True)
    return ranked


def fetch_url(url: str, *, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS, max_chars: int = DEFAULT_MAX_CHARS) -> dict:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {"ok": False, "error": "web_browse requires an http(s) URL."}

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5",
            "Accept-Language": "ja,en-US;q=0.8,en;q=0.6",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            content_type = resp.headers.get("Content-Type", "")
            final_url = resp.geturl()
            raw = resp.read(2_000_000)
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.reason}", "url": url}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"Network error: {e.reason}", "url": url}
    except TimeoutError:
        return {"ok": False, "error": "Request timed out.", "url": url}

    decoded = _decode_response(raw, content_type)
    links: list[tuple[str, str]] = []
    if "html" in content_type.lower() or "<html" in decoded[:1000].lower():
        parser = _ReadableTextParser()
        parser.feed(decoded)
        title = parser.title()
        text = parser.text()
        links = parser.links()
    else:
        title = ""
        text = _normalize_text(decoded)

    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + f"\n[truncated at {max_chars} chars]"
    return {
        "ok": True,
        "url": final_url,
        "title": title,
        "content_type": content_type,
        "text": text,
        "links": links,
    }


def browse_query(
    query: str,
    *,
    max_pages: int = 3,
    max_chars_per_page: int = DEFAULT_MAX_CHARS,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> list[dict]:
    from backend.web_search_service import perform_web_search

    max_depth = max(0, min(int(max_depth), 2))
    candidate_limit = max(8, max_pages * 4)
    search_results = perform_web_search(query, max_results=candidate_limit)
    pages: list[dict] = []
    seen_urls: set[str] = set()
    queued_urls: set[str] = set()
    domain_counts: dict[str, int] = {}
    queue: deque[dict] = deque()

    seed_budget = max(1, min(max_pages, (max_pages + 1) // 2 if max_depth else max_pages))
    for result in search_results:
        url = result.get("url") if isinstance(result, dict) else None
        if not isinstance(url, str) or not url.strip():
            continue
        url = _normalized_url(url.strip())
        if url in queued_urls or _is_search_result_page(url) or not _is_public_discovered_url(url):
            continue
        queued_urls.add(url)
        queue.append({
            "url": url,
            "depth": 0,
            "parent_url": "",
            "link_text": "",
            "search_title": result.get("title"),
            "search_snippet": result.get("snippet"),
        })
        if len(queue) >= seed_budget:
            break

    while queue and len(pages) < max_pages:
        item = queue.popleft()
        url = item["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        host = _host(url)
        if domain_counts.get(host, 0) >= MAX_RESULTS_PER_DOMAIN:
            continue

        page = fetch_url(url, max_chars=max_chars_per_page)
        if not page.get("ok"):
            continue
        text = str(page.get("text") or "").strip()
        if len(text) < MIN_READABLE_CHARS:
            continue

        page["search_title"] = item.get("search_title")
        page["search_snippet"] = item.get("search_snippet")
        page["source_domain"] = host
        page["depth"] = item["depth"]
        page["parent_url"] = item.get("parent_url") or ""
        page["link_text"] = item.get("link_text") or ""
        pages.append(page)
        domain_counts[host] = domain_counts.get(host, 0) + 1

        if item["depth"] >= max_depth:
            continue
        for link in _rank_links(query, page):
            target = link["url"]
            if target in seen_urls or target in queued_urls:
                continue
            target_host = _host(target)
            if domain_counts.get(target_host, 0) >= MAX_RESULTS_PER_DOMAIN:
                continue
            queued_urls.add(target)
            queue.append({
                "url": target,
                "depth": item["depth"] + 1,
                "parent_url": page.get("url") or url,
                "link_text": link.get("anchor_text") or "",
                "search_title": "",
                "search_snippet": "",
            })
            if len(queue) >= max_pages * 4:
                break

    return pages
