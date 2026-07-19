"""Locale-aware Google Trends RSS reader for SNS post inspiration."""
from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET


GOOGLE_TRENDS_RSS_URL = "https://trends.google.com/trending/rss?geo={geo}"
GOOGLE_TRENDS_NAMESPACE = "https://trends.google.com/trending/rss"

# Used when the browser/OS supplies only a language without a region.
LANGUAGE_DEFAULT_GEOS = {
    "ar": "SA",
    "de": "DE",
    "en": "US",
    "es": "ES",
    "fr": "FR",
    "hi": "IN",
    "id": "ID",
    "ja": "JP",
    "ko": "KR",
    "pt": "BR",
    "vi": "VN",
    "zh": "TW",
}

FALLBACK_RSS_SOURCES = (
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("NPR World", "https://feeds.npr.org/1004/rss.xml"),
)


def _normalize_locale_tag(locale: str | None) -> str:
    value = str(locale or "").strip().replace("_", "-")
    if len(value) > 35 or not re.fullmatch(r"[A-Za-z0-9-]+", value):
        return "en-US"
    return value


def locale_to_geo(locale: str | None) -> str:
    """Resolve a browser/OS BCP 47 locale to a Google Trends country code."""
    normalized = _normalize_locale_tag(locale)
    parts = [part for part in normalized.split("-") if part]
    language = parts[0].lower() if parts else "en"

    for part in parts[1:]:
        if re.fullmatch(r"[A-Za-z]{2}", part):
            region = part.upper()
            return "GB" if region == "UK" else region
    return LANGUAGE_DEFAULT_GEOS.get(language, "US")


def get_top_news(limit: int = 5, locale: str | None = None) -> dict:
    """Return regional search trends with their attached news context."""
    requested_locale = _normalize_locale_tag(locale)
    preferred_geo = locale_to_geo(requested_locale)
    candidate_geos = [preferred_geo]
    language_geo = LANGUAGE_DEFAULT_GEOS.get(
        requested_locale.replace("_", "-").split("-", 1)[0].lower(),
    )
    for fallback_geo in (language_geo, "US"):
        if fallback_geo and fallback_geo not in candidate_geos:
            candidate_geos.append(fallback_geo)

    errors = []
    for geo in candidate_geos:
        url = GOOGLE_TRENDS_RSS_URL.format(geo=geo)
        try:
            root = _read_rss(url)
            items = _parse_google_trends(root, limit=max(1, min(int(limit), 10)))
            if items:
                return {
                    "ok": True,
                    "provider": "Google Trends",
                    "source": f"Google Trends ({geo})",
                    "requested_locale": requested_locale,
                    "geo": geo,
                    "items": items,
                }
            errors.append(f"Google Trends ({geo}): no items")
        except Exception as exc:
            errors.append(f"Google Trends ({geo}): {exc}")

    fallback = _get_fallback_news(limit=max(1, min(int(limit), 5)))
    if fallback.get("ok"):
        fallback.update({
            "requested_locale": requested_locale,
            "requested_geo": preferred_geo,
            "fallback": True,
            "trends_errors": errors,
        })
        return fallback
    errors.append(str(fallback.get("error") or "Fallback RSS failed"))
    return {"ok": False, "error": "; ".join(errors)}


def _read_rss(url: str) -> ET.Element:
    request = urllib.request.Request(url, headers={"User-Agent": "Enchan-SNS/1.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return ET.fromstring(response.read())


def _parse_google_trends(root: ET.Element, limit: int) -> list[dict]:
    namespace = {"ht": GOOGLE_TRENDS_NAMESPACE}
    trends = []
    for item in root.findall(".//item")[:limit]:
        related_news = []
        for news_item in item.findall("ht:news_item", namespace)[:3]:
            related_news.append({
                "title": _text(news_item, "ht:news_item_title", namespace),
                "snippet": _text(news_item, "ht:news_item_snippet", namespace),
                "source": _text(news_item, "ht:news_item_source", namespace),
                "url": _text(news_item, "ht:news_item_url", namespace),
            })
        trends.append({
            "trend": _text(item, "title"),
            "approx_traffic": _text(item, "ht:approx_traffic", namespace),
            "published": _text(item, "pubDate"),
            "related_news": related_news,
        })
    return [item for item in trends if item["trend"]]


def _get_fallback_news(limit: int) -> dict:
    errors = []
    for source, url in FALLBACK_RSS_SOURCES:
        try:
            root = _read_rss(url)
            items = []
            for item in root.findall(".//item")[:limit]:
                items.append({
                    "source": source,
                    "title": _text(item, "title"),
                    "summary": _text(item, "description"),
                    "published": _text(item, "pubDate"),
                    "link": _text(item, "link"),
                })
            if items:
                return {"ok": True, "provider": "news RSS fallback", "source": source, "items": items}
            errors.append(f"{source}: no items")
        except Exception as exc:
            errors.append(f"{source}: {exc}")
    return {"ok": False, "error": "; ".join(errors)}


def _text(element: ET.Element, path: str, namespace: dict | None = None) -> str:
    return (element.findtext(path, default="", namespaces=namespace or {}) or "").strip()
