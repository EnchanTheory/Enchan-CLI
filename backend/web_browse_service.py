import html
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser


DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_MAX_CHARS = 12000
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 EnchanCLI/1.0"
)


class _ReadableTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._chunks: list[str] = []
        self._title: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "canvas", "iframe"}:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
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
        self._chunks.append(text)
        self._chunks.append(" ")

    def title(self) -> str:
        return _normalize_text(" ".join(self._title))

    def text(self) -> str:
        return _normalize_text("".join(self._chunks))


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
    if "html" in content_type.lower() or "<html" in decoded[:1000].lower():
        parser = _ReadableTextParser()
        parser.feed(decoded)
        title = parser.title()
        text = parser.text()
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
    }


def browse_query(query: str, *, max_pages: int = 3, max_chars_per_page: int = DEFAULT_MAX_CHARS) -> list[dict]:
    from backend.web_search_service import perform_web_search

    search_results = perform_web_search(query, max_results=max(3, max_pages * 2))
    pages: list[dict] = []
    ok_count = 0
    for result in search_results:
        url = result.get("url") if isinstance(result, dict) else None
        if not url:
            continue
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            continue
        page = fetch_url(url, max_chars=max_chars_per_page)
        page["search_title"] = result.get("title")
        page["search_snippet"] = result.get("snippet")
        pages.append(page)
        if page.get("ok"):
            ok_count += 1
        if ok_count >= max_pages:
            break
    return pages
