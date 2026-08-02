"""Provider-neutral TTS manager used by the local Web UI."""

from __future__ import annotations

import ipaddress
import json
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


MAX_TEXT_CHARS = 10_000
MAX_AUDIO_BYTES = 32 * 1024 * 1024
PROVIDER_PRESETS = {
    "browser": {"host": "127.0.0.1", "port": 0},
    "bouyomi": {"host": "127.0.0.1", "port": 50080},
    "voicevox": {"host": "127.0.0.1", "port": 50021},
    "coeiroink": {"host": "127.0.0.1", "port": 50031},
    "aivis": {"host": "127.0.0.1", "port": 10101},
    "openai": {"host": "127.0.0.1", "port": 8000},
    "http": {"host": "127.0.0.1", "port": 50021},
}
SUPPORTED_PROVIDERS = frozenset(PROVIDER_PRESETS)


@dataclass(frozen=True)
class TTSResult:
    audio: bytes = b""
    content_type: str = "audio/wav"
    external_playback: bool = False


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def speech_text(value: str) -> str:
    """Reduce display Markdown to readable speech without tool/code noise."""
    text = str(value or "").strip()
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"^\s{0,3}(?:#{1,6}|>|[-*+] |\d+[.)] )\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_~]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        raise ValueError("There is no readable text")
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS].rsplit(" ", 1)[0] or text[:MAX_TEXT_CHARS]
    return text


class TTSManager:
    def __init__(self, data_dir: Path):
        self._directory = Path(data_dir)
        self._settings_path = self._directory / "settings.json"
        self._lock = threading.RLock()
        self._opener = build_opener(_NoRedirect())

    @staticmethod
    def defaults() -> dict[str, Any]:
        return {
            "enabled": False,
            "autoSpeak": True,
            "provider": "browser",
            "host": "127.0.0.1",
            "port": 0,
            "voice": "",
            "speaker": 0,
            "baseUrl": "",
            "path": "/v1/audio/speech",
            "model": "tts-1",
            "format": "mp3",
            "speed": 1.0,
            "instructions": "",
            "apiKeyEnv": "OPENAI_API_KEY",
            "allowRemote": False,
            "method": "POST",
            "bodyFormat": "json",
            "textField": "text",
            "responseMode": "audio",
            "headers": {},
        }

    def settings(self) -> dict[str, Any]:
        with self._lock:
            try:
                saved = json.loads(self._settings_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                saved = {}
            merged = self.defaults()
            if isinstance(saved, dict):
                merged.update(saved)
            return self._validate(merged)

    def save(self, incoming: dict[str, Any]) -> dict[str, Any]:
        current = self.settings()
        current.update(incoming)
        clean = self._validate(current)
        with self._lock:
            self._directory.mkdir(parents=True, exist_ok=True)
            temporary = self._settings_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self._settings_path)
        return clean

    def public_status(self) -> dict[str, Any]:
        settings = self.settings()
        return {"settings": settings, "providers": sorted(SUPPORTED_PROVIDERS)}

    def voices(self) -> list[dict[str, Any]]:
        settings = self.settings()
        provider = settings["provider"]
        if provider not in {"voicevox", "coeiroink", "aivis"}:
            return []
        payload, _ = self._request(settings, "GET", "/speakers")
        speakers = json.loads(payload.decode("utf-8"))
        result = []
        for speaker in speakers if isinstance(speakers, list) else []:
            for style in speaker.get("styles", []):
                result.append({
                    "id": int(style.get("id", 0)),
                    "name": f"{speaker.get('name', '')} / {style.get('name', '')}".strip(" /"),
                })
        return result

    def synthesize(self, raw_text: str) -> TTSResult:
        settings = self.settings()
        if not settings["enabled"]:
            raise RuntimeError("TTS is disabled")
        text = speech_text(raw_text)
        provider = settings["provider"]
        if provider == "browser":
            raise ValueError("Browser speech is synthesized in the browser")
        if provider in {"voicevox", "coeiroink", "aivis"}:
            return self._voicevox(settings, text)
        if provider == "bouyomi":
            self._request(settings, "GET", "/Talk", query={"text": text})
            return TTSResult(external_playback=True)
        if provider == "openai":
            return self._openai(settings, text)
        return self._generic_http(settings, text)

    def _voicevox(self, settings: dict[str, Any], text: str) -> TTSResult:
        speaker = int(settings["speaker"])
        query, _ = self._request(
            settings, "POST", "/audio_query", query={"text": text, "speaker": speaker}, body=b""
        )
        audio, content_type = self._request(
            settings, "POST", "/synthesis", query={"speaker": speaker}, body=query,
            headers={"Content-Type": "application/json"},
        )
        return TTSResult(audio, content_type if content_type.startswith("audio/") else "audio/wav")

    def _openai(self, settings: dict[str, Any], text: str) -> TTSResult:
        payload: dict[str, Any] = {
            "model": settings["model"], "voice": settings["voice"], "input": text,
            "response_format": settings["format"], "speed": settings["speed"],
        }
        if settings["instructions"]:
            payload["instructions"] = settings["instructions"]
        headers = {"Content-Type": "application/json"}
        api_key = os.environ.get(settings["apiKeyEnv"], "") if settings["apiKeyEnv"] else ""
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        audio, content_type = self._request(
            settings, "POST", settings["path"], body=json.dumps(payload).encode("utf-8"), headers=headers,
        )
        return TTSResult(audio, content_type if content_type.startswith("audio/") else self._format_content_type(settings["format"]))

    def _generic_http(self, settings: dict[str, Any], text: str) -> TTSResult:
        method = settings["method"]
        body_format = settings["bodyFormat"]
        field = settings["textField"]
        headers = self._resolved_headers(settings["headers"])
        query = None
        body = None
        if method == "GET" or body_format == "query":
            query = {field: text}
        elif body_format == "form":
            body = urlencode({field: text}).encode("utf-8")
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        else:
            body = json.dumps({field: text}, ensure_ascii=False).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        payload, content_type = self._request(settings, method, settings["path"], query=query, body=body, headers=headers)
        if settings["responseMode"] == "external":
            return TTSResult(external_playback=True)
        return TTSResult(payload, content_type or "application/octet-stream")

    def _request(
        self, settings: dict[str, Any], method: str, path: str, *, query: dict[str, Any] | None = None,
        body: bytes | None = None, headers: dict[str, str] | None = None,
    ) -> tuple[bytes, str]:
        url = self._url(settings, path)
        if query:
            url += ("&" if "?" in url else "?") + urlencode(query)
        request = Request(url, data=body, headers=headers or {}, method=method)
        try:
            with self._opener.open(request, timeout=60) as response:
                payload = response.read(MAX_AUDIO_BYTES + 1)
                if len(payload) > MAX_AUDIO_BYTES:
                    raise ValueError("TTS response is larger than 32 MB")
                return payload, response.headers.get_content_type()
        except HTTPError as exc:
            detail = exc.read(1000).decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"TTS service returned HTTP {exc.code}: {detail or exc.reason}") from exc
        except URLError as exc:
            raise RuntimeError(f"Could not connect to the TTS service: {exc.reason}") from exc

    def _url(self, settings: dict[str, Any], path: str) -> str:
        base = settings["baseUrl"].strip()
        if not base:
            base = f"http://{settings['host']}:{settings['port']}"
        parsed = urlparse(base)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("TTS URL must use http or https")
        if parsed.username or parsed.password:
            raise ValueError("TTS URL must not contain credentials")
        target = urlparse(path)
        if target.scheme or target.netloc or path.startswith("//"):
            raise ValueError("TTS API path must be relative to the base URL")
        if not settings["allowRemote"] and not self._is_loopback(parsed.hostname):
            raise PermissionError("Remote TTS URLs require explicit permission")
        return urljoin(base.rstrip("/") + "/", path.lstrip("/"))

    @staticmethod
    def _is_loopback(host: str) -> bool:
        if host.lower() == "localhost":
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    @staticmethod
    def _resolved_headers(headers: dict[str, str]) -> dict[str, str]:
        result = {}
        for name, value in headers.items():
            result[name] = re.sub(
                r"[$][{]([A-Z_][A-Z0-9_]*)[}]",
                lambda match: os.environ.get(match.group(1), ""),
                value,
            )
        return result

    @staticmethod
    def _format_content_type(value: str) -> str:
        return {"mp3": "audio/mpeg", "wav": "audio/wav", "opus": "audio/ogg", "aac": "audio/aac", "flac": "audio/flac"}.get(value, "application/octet-stream")

    @staticmethod
    def _validate(value: dict[str, Any]) -> dict[str, Any]:
        clean = TTSManager.defaults()
        provider = str(value.get("provider", "browser")).strip().lower()
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError("Unsupported TTS provider")
        clean["provider"] = provider
        for key in ("enabled", "autoSpeak", "allowRemote"):
            clean[key] = bool(value.get(key, clean[key]))
        clean["host"] = str(value.get("host", "") or PROVIDER_PRESETS[provider]["host"]).strip()[:255]
        clean["port"] = int(value.get("port", PROVIDER_PRESETS[provider]["port"]))
        if not 0 <= clean["port"] <= 65535:
            raise ValueError("TTS port must be between 0 and 65535")
        clean["speaker"] = max(0, int(value.get("speaker", 0)))
        for key, maximum in (("voice", 100), ("baseUrl", 1000), ("path", 500), ("model", 200), ("format", 20), ("instructions", 1000), ("apiKeyEnv", 100), ("textField", 100)):
            clean[key] = str(value.get(key, clean[key])).strip()[:maximum]
        clean["speed"] = min(4.0, max(0.25, float(value.get("speed", 1.0))))
        clean["method"] = str(value.get("method", "POST")).upper()
        if clean["method"] not in {"GET", "POST"}:
            raise ValueError("Generic HTTP method must be GET or POST")
        clean["bodyFormat"] = str(value.get("bodyFormat", "json")).lower()
        if clean["bodyFormat"] not in {"json", "form", "query"}:
            raise ValueError("Unsupported generic HTTP body format")
        clean["responseMode"] = str(value.get("responseMode", "audio")).lower()
        if clean["responseMode"] not in {"audio", "external"}:
            raise ValueError("Unsupported generic HTTP response mode")
        raw_headers = value.get("headers", {})
        if not isinstance(raw_headers, dict) or len(raw_headers) > 20:
            raise ValueError("TTS headers must be an object with at most 20 entries")
        clean["headers"] = {str(k).strip()[:100]: str(v).strip()[:1000] for k, v in raw_headers.items() if str(k).strip()}
        for name, header_value in clean["headers"].items():
            if name.lower() in {"authorization", "proxy-authorization", "x-api-key", "api-key"} and not re.search(r"[$][{][A-Z_][A-Z0-9_]*[}]", header_value):
                raise ValueError(f"{name} must reference an environment variable")
        if provider == "openai" and not clean["voice"]:
            clean["voice"] = "alloy"
        return clean
