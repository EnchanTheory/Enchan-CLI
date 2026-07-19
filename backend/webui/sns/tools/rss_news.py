"""Small RSS reader for external news as inspiration, not text reproduction."""
import urllib.request
import xml.etree.ElementTree as ET

RSS_SOURCES = (
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("NPR World", "https://feeds.npr.org/1004/rss.xml"),
)

def get_top_news(limit: int = 3) -> dict:
    errors = []
    for source, url in RSS_SOURCES:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Enchan-SNS/1.0"})
            with urllib.request.urlopen(request, timeout=10) as response:
                root = ET.fromstring(response.read())
            items = []
            for item in root.findall(".//item")[:limit]:
                items.append({
                    "source": source,
                    "title": (item.findtext("title") or "").strip(),
                    "summary": (item.findtext("description") or "").strip(),
                    "published": (item.findtext("pubDate") or "").strip(),
                    "link": (item.findtext("link") or "").strip(),
                })
            if items:
                return {"ok": True, "source": source, "items": items}
            errors.append(f"{source}: no items")
        except Exception as exc:
            errors.append(f"{source}: {exc}")
    return {"ok": False, "error": "; ".join(errors)}
