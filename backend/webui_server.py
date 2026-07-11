"""Local browser interface for Enchan CLI."""

from __future__ import annotations

import base64
import json
import mimetypes
import re
import struct
import threading
import time
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from backend.agent_tools import get_agent_system_prompt
from backend.context_compression import count_text_tokens
from backend.memory_store import build_memory_prompt_section, load_memory_context
from backend.session_log import append_session_event
from backend.tokenizer_bridge import estimate_text_tokens_rough

BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent
WEB_DIR = BACKEND_DIR / "webui"
BUILTIN_MASCOT_DIR = WEB_DIR / "mascots"
MASCOT_DIR = CLI_DIR / "data" / "mascots"
MASCOT_CONFIG = MASCOT_DIR / "mascots.json"
MAX_BODY_BYTES = 20 * 1024 * 1024
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")

# Codex Pets v4 contact-sheet contract: 192x208 frames in an 8x9 grid.
CODEX_FRAME = {"width": 192, "height": 208, "columns": 8, "rows": 9}
CODEX_ANIMATIONS = {
    "idle": {"frames": [0, 1, 2, 3, 4, 5], "durations": [1680, 660, 660, 840, 840, 1920], "loop": True},
    "running-right": {"row": 1, "count": 8, "frameDuration": 120, "finalDuration": 220, "repeats": 3},
    "running-left": {"row": 2, "count": 8, "frameDuration": 120, "finalDuration": 220, "repeats": 3},
    "waving": {"row": 3, "count": 4, "frameDuration": 140, "finalDuration": 280, "repeats": 3},
    "jumping": {"row": 4, "count": 5, "frameDuration": 140, "finalDuration": 280, "repeats": 3},
    "failed": {"row": 5, "count": 8, "frameDuration": 140, "finalDuration": 240, "repeats": 3},
    "waiting": {"row": 6, "count": 6, "frameDuration": 150, "finalDuration": 260, "repeats": 3},
    "running": {"row": 7, "count": 6, "frameDuration": 120, "finalDuration": 220, "repeats": 3},
    "review": {"row": 8, "count": 6, "frameDuration": 150, "finalDuration": 280, "repeats": 3},
}


def _default_store() -> dict[str, Any]:
    manifest_path = BUILTIN_MASCOT_DIR / "tikta" / "pet.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {"selected": "tikta", "mascots": [{
        "id": manifest["id"],
        "name": manifest["displayName"],
        "description": manifest["description"],
        "personality": manifest["personality"],
        "spritesheet": manifest["spritesheetPath"],
        "builtin": True,
    }]}


def _load_store() -> dict[str, Any]:
    if not MASCOT_CONFIG.exists():
        return _default_store()
    try:
        data = json.loads(MASCOT_CONFIG.read_text(encoding="utf-8"))
        if not isinstance(data.get("mascots"), list):
            raise ValueError("mascots must be a list")
        return data
    except Exception:
        return _default_store()


def _save_store(data: dict[str, Any]) -> None:
    MASCOT_DIR.mkdir(parents=True, exist_ok=True)
    temp = MASCOT_CONFIG.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(MASCOT_CONFIG)


def _image_dimensions(raw: bytes, image_type: str) -> tuple[int, int]:
    if image_type == "png" and raw.startswith(b"\x89PNG\r\n\x1a\n") and len(raw) >= 24:
        return struct.unpack(">II", raw[16:24])
    if image_type == "webp" and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        chunk = raw[12:16]
        if chunk == b"VP8X" and len(raw) >= 30:
            return (1 + int.from_bytes(raw[24:27], "little"),
                    1 + int.from_bytes(raw[27:30], "little"))
        if chunk == b"VP8L" and len(raw) >= 25 and raw[20] == 0x2F:
            bits = int.from_bytes(raw[21:25], "little")
            return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
        if chunk == b"VP8 " and len(raw) >= 30 and raw[23:26] == b"\x9d\x01\x2a":
            return (int.from_bytes(raw[26:28], "little") & 0x3FFF,
                    int.from_bytes(raw[28:30], "little") & 0x3FFF)
    raise ValueError("Could not read spritesheet dimensions")


@dataclass
class WebChatState:
    backend_mode: str
    args: Any
    session_log_path: Path
    generation_config: dict[str, Any]
    tokenizer: Any
    agent_mode: bool

    def __post_init__(self) -> None:
        self.chat_history: list[dict[str, Any]] = []
        self.lock = threading.Lock()

    def public_config(self) -> dict[str, Any]:
        store = _load_store()
        return {
            "backend": self.backend_mode,
            "model": self.generation_config.get("model_id", ""),
            "agentMode": self.agent_mode,
            "selectedMascot": store.get("selected", "tikta"),
            "mascots": store.get("mascots", []),
            "frame": CODEX_FRAME,
            "animations": CODEX_ANIMATIONS,
        }

    def reset(self) -> None:
        with self.lock:
            self.chat_history.clear()

    def chat_stream(self, prompt: str) -> Any:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Message is empty")
        if len(prompt) > 1_000_000:
            raise ValueError("Message is too large")

        import queue
        q = queue.Queue()

        def worker():
            with self.lock:
                try:
                    input_tokens = count_text_tokens(self.tokenizer, prompt) if self.tokenizer else estimate_text_tokens_rough(prompt)
                    if input_tokens > int(self.generation_config["max_input_tokens"]):
                        raise ValueError("Message exceeds the configured context limit")

                    store = _load_store()
                    selected = next((m for m in store["mascots"] if m.get("id") == store.get("selected")), None)
                    personality = (selected or {}).get("personality", "").strip()
                    system_context = get_agent_system_prompt() + build_memory_prompt_section(load_memory_context())
                    if personality:
                        system_context += f"\n\nCharacter persona for this conversation:\n{personality}"
                    config = dict(self.generation_config)
                    config["system_context"] = system_context
                    config["suppress_response_header"] = True

                    self.chat_history.append({"role": "user", "content": prompt})
                    append_session_event(self.session_log_path, {
                        "type": "message", "role": "user", "content": prompt,
                        "input_tokens_estimate": input_tokens, "backend": self.backend_mode, "interface": "web",
                    })

                    def on_chunk(chunk: str):
                        q.put({"type": "chunk", "text": chunk})

                    result = self._run_agent_turn(config, chunk_callback=on_chunk)
                    if not result:
                        self.chat_history.pop()
                        q.put({"type": "error", "error": "The model did not return a response"})
                        return
                    q.put({"type": "done", "result": result})
                except Exception as e:
                    if self.chat_history and self.chat_history[-1].get("role") == "user":
                        self.chat_history.pop()
                    q.put({"type": "error", "error": str(e)})

        threading.Thread(target=worker, daemon=True).start()

        while True:
            item = q.get()
            if item["type"] == "chunk":
                yield item["text"]
            elif item["type"] == "done":
                break
            elif item["type"] == "error":
                raise RuntimeError(item["error"])

    def chat(self, prompt: str) -> dict[str, Any]:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Message is empty")
        if len(prompt) > 1_000_000:
            raise ValueError("Message is too large")
        with self.lock:
            input_tokens = count_text_tokens(self.tokenizer, prompt) if self.tokenizer else estimate_text_tokens_rough(prompt)
            if input_tokens > int(self.generation_config["max_input_tokens"]):
                raise ValueError("Message exceeds the configured context limit")

            store = _load_store()
            selected = next((m for m in store["mascots"] if m.get("id") == store.get("selected")), None)
            personality = (selected or {}).get("personality", "").strip()
            system_context = get_agent_system_prompt() + build_memory_prompt_section(load_memory_context())
            if personality:
                system_context += f"\n\nCharacter persona for this conversation:\n{personality}"
            config = dict(self.generation_config)
            config["system_context"] = system_context
            config["suppress_response_header"] = True

            self.chat_history.append({"role": "user", "content": prompt})
            append_session_event(self.session_log_path, {
                "type": "message", "role": "user", "content": prompt,
                "input_tokens_estimate": input_tokens, "backend": self.backend_mode, "interface": "web",
            })
            try:
                result = self._run_agent_turn(config)
            except Exception:
                self.chat_history.pop()
                raise
            if not result:
                self.chat_history.pop()
                raise RuntimeError("The model did not return a response")
            response = result.get("response", "")
            return {"response": response, "thinking": result.get("thinking", ""), "metrics": {
                "elapsed": result.get("elapsed_sec"), "tps": result.get("tps"),
            }}

    def _run_agent_turn(self, config: dict[str, Any], chunk_callback: Any = None) -> dict[str, Any] | None:
        from backend.agent_loop import run_agent_loop

        if self.backend_mode == "enchan":
            from backend.cancellable_backends import generate_enchan_llama_response
            from backend.enchan_llama_backend import (
                DEFAULT_ENCHAN_LLAMA_PORT,
                append_tool_result_event,
                ensure_enchan_llama_for_request,
            )
            if not ensure_enchan_llama_for_request(config, self.args):
                raise RuntimeError("Failed to start the Enchan engine")
            generate = lambda: generate_enchan_llama_response(
                self.chat_history, config, self.session_log_path,
                host=f"http://localhost:{DEFAULT_ENCHAN_LLAMA_PORT}",
                stream_output=False, show_metrics=False,
                chunk_callback=chunk_callback,
            )
        else:
            from backend.ollama_backend import append_tool_result_event, generate_ollama_response
            generate = lambda: generate_ollama_response(
                self.chat_history, config, self.session_log_path,
                self.args.ollama_host, self.args.ollama_model,
                view_think=False, stream_output=False, show_metrics=False,
                chunk_callback=chunk_callback,
            )

        history_start = len(self.chat_history)
        run_agent_loop(
            chat_history=self.chat_history,
            generation_config=config,
            session_log_path=self.session_log_path,
            backend=self.backend_mode,
            generate_response=generate,
            append_tool_result_event=append_tool_result_event,
            tokenizer=self.tokenizer,
            plain=True,
        )
        for message in reversed(self.chat_history[history_start:]):
            if message.get("role") in ("assistant", "model") and not message.get("tool_calls"):
                return {
                    "response": message.get("content", ""),
                    "thinking": message.get("thinking", ""),
                }
        return None


class WebUIHandler(BaseHTTPRequestHandler):
    server_version = "EnchanWebUI/1.0"

    @property
    def state(self) -> WebChatState:
        return self.server.state  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[Web UI] {self.address_string()} {fmt % args}")

    def _json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY_BYTES:
            raise ValueError("Invalid request size")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path == "/api/config":
            self._json(HTTPStatus.OK, self.state.public_config())
            return
        if path.startswith("/api/mascots/"):
            self._serve_mascot(path.removeprefix("/api/mascots/"))
            return
        relative = "index.html" if path == "/" else path.lstrip("/")
        asset = (WEB_DIR / relative).resolve()
        if (WEB_DIR.resolve() not in asset.parents and asset != WEB_DIR.resolve()) or not asset.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._serve_file(asset)

    def _serve_mascot(self, mascot_id: str) -> None:
        if not ID_PATTERN.fullmatch(mascot_id):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        store = _load_store()
        mascot = next((m for m in store["mascots"] if m.get("id") == mascot_id), None)
        base_dir = BUILTIN_MASCOT_DIR if (mascot or {}).get("builtin") else MASCOT_DIR
        asset = base_dir / mascot_id / str((mascot or {}).get("spritesheet", ""))
        if not mascot or not asset.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._serve_file(asset, no_cache=True)

    def _serve_file(self, asset: Path, no_cache: bool = False) -> None:
        body = asset.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(asset.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        if no_cache:
            self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        try:
            data = self._read_json()
            if self.path == "/api/client/heartbeat":
                self.server.mark_client(str(data.get("clientId", "")))  # type: ignore[attr-defined]
                self._json(HTTPStatus.OK, {"ok": True})
            elif self.path == "/api/client/close":
                self.server.remove_client(str(data.get("clientId", "")))  # type: ignore[attr-defined]
                self._json(HTTPStatus.OK, {"ok": True})
            elif self.path == "/api/chat":
                self._json(HTTPStatus.OK, self.state.chat(str(data.get("message", ""))))
            elif self.path == "/api/chat_stream":
                message = str(data.get("message", ""))
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                for chunk in self.state.chat_stream(message):
                    # Replace newlines with something safe or encode as JSON
                    payload = json.dumps({"chunk": chunk}, ensure_ascii=False)
                    self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.write(b"data: [DONE]\n\n")
            elif self.path == "/api/new":
                self.state.reset()
                self._json(HTTPStatus.OK, {"ok": True})
            elif self.path == "/api/mascots/select":
                self._select_mascot(str(data.get("id", "")))
                self._json(HTTPStatus.OK, self.state.public_config())
            elif self.path == "/api/mascots":
                self._save_mascot(data)
                self._json(HTTPStatus.OK, self.state.public_config())
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def _select_mascot(self, mascot_id: str) -> None:
        store = _load_store()
        if not any(m.get("id") == mascot_id for m in store["mascots"]):
            raise ValueError("Unknown mascot")
        store["selected"] = mascot_id
        _save_store(store)

    def _save_mascot(self, data: dict[str, Any]) -> None:
        mascot_id = str(data.get("id", "")).strip().lower()
        if not ID_PATTERN.fullmatch(mascot_id):
            raise ValueError("ID must use lowercase letters, numbers, hyphens, or underscores")
        name = str(data.get("name", "")).strip()[:80]
        if not name:
            raise ValueError("Name is required")
        store = _load_store()
        current = next((m for m in store["mascots"] if m.get("id") == mascot_id), None)
        filename = (current or {}).get("spritesheet", "")
        image_data = str(data.get("image", ""))
        if image_data:
            match = re.fullmatch(r"data:image/(png|webp);base64,([A-Za-z0-9+/=]+)", image_data)
            if not match:
                raise ValueError("Spritesheet must be a PNG or WebP image")
            raw = base64.b64decode(match.group(2), validate=True)
            if len(raw) > 15 * 1024 * 1024:
                raise ValueError("Spritesheet exceeds 15 MB")
            dimensions = _image_dimensions(raw, match.group(1))
            filename = f"spritesheet.{match.group(1)}"
            target = MASCOT_DIR / mascot_id
            target.mkdir(parents=True, exist_ok=True)
            (target / filename).write_bytes(raw)
        if mascot_id != "tikta" and not filename:
            raise ValueError("A Codex-compatible spritesheet is required")
        record = {
            "id": mascot_id, "name": name,
            "description": str(data.get("description", "")).strip()[:240],
            "personality": str(data.get("personality", "")).strip()[:12000],
            "spritesheet": filename, "builtin": mascot_id == "tikta",
        }
        store["mascots"] = [m for m in store["mascots"] if m.get("id") != mascot_id] + [record]
        store["selected"] = mascot_id
        _save_store(store)


class EnchanWebServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], state: WebChatState):
        super().__init__(address, WebUIHandler)
        self.state = state
        self._clients: dict[str, float] = {}
        self._client_lock = threading.Lock()
        self._ever_had_client = False
        self._empty_since: float | None = None
        self._watchdog_stop = threading.Event()
        self._watchdog = threading.Thread(
            target=self._watch_clients,
            name="enchan-webui-client-watchdog",
            daemon=True,
        )
        self._watchdog.start()

    def mark_client(self, client_id: str) -> None:
        if not client_id:
            return
        with self._client_lock:
            self._clients[client_id] = time.monotonic()
            self._ever_had_client = True
            self._empty_since = None

    def remove_client(self, client_id: str) -> None:
        with self._client_lock:
            self._clients.pop(client_id, None)
            if self._ever_had_client and not self._clients and self._empty_since is None:
                self._empty_since = time.monotonic()

    def _watch_clients(self) -> None:
        while not self._watchdog_stop.wait(1.0):
            now = time.monotonic()
            should_shutdown = False
            with self._client_lock:
                stale = [client_id for client_id, seen in self._clients.items() if now - seen > 120]
                for client_id in stale:
                    self._clients.pop(client_id, None)
                if self._ever_had_client and not self._clients:
                    if self._empty_since is None:
                        self._empty_since = now
                    elif now - self._empty_since >= 5:
                        should_shutdown = True
                else:
                    self._empty_since = None
            if should_shutdown:
                threading.Thread(target=self.shutdown, name="enchan-webui-shutdown", daemon=True).start()
                return

    def server_close(self) -> None:
        self._watchdog_stop.set()
        super().server_close()


def run_webui(*, backend_mode: str, args: Any, session_log_path: Path,
              generation_config: dict[str, Any], tokenizer: Any, agent_mode: bool) -> None:
    if backend_mode == "enchan":
        from backend.kv_cache_config import apply_enchan_kv_cache_patch
        generation_config["kv_cache_type"] = apply_enchan_kv_cache_patch(getattr(args, "kv_cache_type", None))
        generation_config["screen_strength"] = getattr(args, "screen_strength", 0.2)
    state = WebChatState(backend_mode, args, session_log_path, generation_config, tokenizer, agent_mode)
    server = EnchanWebServer((args.web_host, args.web_port), state)
    host, port = server.server_address[:2]
    browser_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    url = f"http://{browser_host}:{port}/"
    print(f"[Web UI] Running at {url}")
    print("[Web UI] Press Ctrl+C to stop.")
    threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if backend_mode == "enchan":
            from backend.enchan_llama_backend import request_enchan_llama_shutdown
            request_enchan_llama_shutdown()
