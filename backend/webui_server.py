"""Local browser interface for Enchan CLI."""

from __future__ import annotations

import base64
import json
import mimetypes
import re
import struct
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from backend.agent_tools import get_agent_system_prompt
from backend.context_compression import count_text_tokens
from backend.memory_store import build_memory_prompt_section, load_memory_context
from backend.approval import ApprovalDecision, ApprovalRequest, approval_scope
from backend.session_log import append_session_event
from backend.rag.jobs import RAGIndexJobManager
from backend.rag.service import RAGService
from backend.tokenizer_bridge import estimate_text_tokens_rough
from backend.social_broker import SocialBroker


BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent
WEB_DIR = BACKEND_DIR / "webui"
BUILTIN_MASCOT_DIR = WEB_DIR / "mascots"
MASCOT_DIR = CLI_DIR / "data" / "mascots"
MASCOT_CONFIG = MASCOT_DIR / "mascots.json"
MAX_BODY_BYTES = 20 * 1024 * 1024
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
WEB_UI_CONTENT_SECURITY_POLICY = "; ".join((
    "default-src 'self'",
    "base-uri 'none'",
    "connect-src 'self' data:",
    "font-src 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "img-src 'self' data: blob: https://storage.googleapis.com",
    "media-src 'self' data: blob:",
    "object-src 'none'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "worker-src 'none'",
))

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


def _select_directory_dialog() -> str | None:
    """Open the host OS directory picker and return an absolute local path."""
    if sys.platform == "darwin":
        script = 'POSIX path of (choose folder with prompt "Select a RAG source directory")'
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
        if "User canceled" in result.stderr:
            return None
        raise RuntimeError(result.stderr.strip() or "Could not open the directory picker")

    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as exc:
        raise RuntimeError("The local Python runtime does not provide a directory picker") from exc
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(parent=root, mustexist=True, title="Select a RAG source directory")
        return str(Path(selected).resolve()) if selected else None
    finally:
        root.destroy()


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
class _PendingApproval:
    request: ApprovalRequest
    client_id: str
    event: threading.Event = field(default_factory=threading.Event)
    decision: ApprovalDecision | None = None


class WebApprovalBroker:
    def __init__(self, timeout_seconds: float = 120.0) -> None:
        self.timeout_seconds = max(0.01, timeout_seconds)
        self._lock = threading.Lock()
        self._pending: _PendingApproval | None = None

    def request(self, request: ApprovalRequest, client_id: str, emit: Any) -> ApprovalDecision:
        pending = _PendingApproval(request=request, client_id=client_id)
        with self._lock:
            if self._pending is not None:
                return ApprovalDecision(False, "approval_already_pending")
            self._pending = pending
        try:
            emit({"type": "approval_required", "request": request.public_dict()})
            signalled = pending.event.wait(self.timeout_seconds)
            with self._lock:
                if not signalled and pending.decision is None:
                    pending.decision = ApprovalDecision(False, "timeout")
                decision = pending.decision or ApprovalDecision(False, "timeout")
            try:
                emit({
                    "type": "approval_resolved",
                    "requestId": request.id,
                    "approved": decision.approved,
                    "reason": decision.reason,
                })
            except Exception:
                pass
            return decision
        except Exception:
            return ApprovalDecision(False, "presentation_error")
        finally:
            with self._lock:
                if self._pending is pending:
                    self._pending = None

    def resolve(self, request_id: str, client_id: str, approved: bool) -> None:
        with self._lock:
            pending = self._pending
            if pending is None or pending.request.id != request_id:
                raise LookupError("Approval request is stale or unknown")
            if pending.client_id != client_id:
                raise PermissionError("Approval request belongs to another browser client")
            if pending.decision is not None:
                raise LookupError("Approval request has already been resolved")
            pending.decision = ApprovalDecision(approved, "user_approved" if approved else "user_denied")
            pending.event.set()

    def cancel_client(self, client_id: str, reason: str = "client_disconnected") -> None:
        with self._lock:
            pending = self._pending
            if pending is not None and pending.client_id == client_id and pending.decision is None:
                pending.decision = ApprovalDecision(False, reason)
                pending.event.set()

    def cancel_all(self, reason: str) -> None:
        with self._lock:
            pending = self._pending
            if pending is not None and pending.decision is None:
                pending.decision = ApprovalDecision(False, reason)
                pending.event.set()

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
        self._activity_lock = threading.Lock()
        self._directory_dialog_lock = threading.Lock()
        self._chat_active = False
        timeout = float(self.generation_config.get("approval_timeout_seconds", 120))
        self.approvals = WebApprovalBroker(timeout)
        self.rag_service = RAGService()
        self.session_collection = self.rag_service.ensure_session_collection(CLI_DIR / "logs" / "sessions")
        self.rag_jobs = RAGIndexJobManager(self.rag_service, self.generation_config)
        self.social_broker = SocialBroker(CLI_DIR / "data" / "social")

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
        self.approvals.cancel_all("new_chat")
        with self.lock:
            self.chat_history.clear()

    @staticmethod
    def _validate_chat_request(prompt: str, client_id: str) -> None:
        if not prompt.strip():
            raise ValueError("Message is empty")
        if not client_id.strip():
            raise ValueError("Browser client ID is required")
        if len(prompt) > 1_000_000:
            raise ValueError("Message is too large")

    def reserve_chat(self, prompt: str, client_id: str) -> None:
        self._validate_chat_request(prompt, client_id)
        with self._activity_lock:
            if self.rag_jobs.is_busy():
                raise RuntimeError("RAG indexing is running. Chat is available again after completion or interruption.")
            if self._chat_active:
                raise RuntimeError("Another chat response is already running")
            self._chat_active = True

    def rag_status(self) -> dict[str, Any]:
        collections = []
        for collection in self.rag_service.list_collection_statuses():
            item = dict(collection)
            item["required"] = item.get("source_type") == "sessions"
            item["job"] = self.rag_jobs.collection_job(item["id"])
            collections.append(item)
        return {"job": self.rag_jobs.status(), "collections": collections}

    def select_rag_directory(self) -> str | None:
        if not self._directory_dialog_lock.acquire(blocking=False):
            raise RuntimeError("A directory picker is already open")
        try:
            return _select_directory_dialog()
        finally:
            self._directory_dialog_lock.release()

    @staticmethod
    def _validate_rag_metadata(title: str, description: str) -> tuple[str, str]:
        title = title.strip()
        description = description.strip()
        if not title:
            raise ValueError("RAG title is required")
        if not description:
            raise ValueError("RAG description is required")
        if len(title) > 120:
            raise ValueError("RAG title must be 120 characters or fewer")
        if len(description) > 500:
            raise ValueError("RAG description must be 500 characters or fewer")
        return title, description

    def register_rag_directory(self, source_path: str, title: str, description: str) -> dict[str, Any]:
        if not source_path.strip():
            raise ValueError("RAG source directory is required")
        title, description = self._validate_rag_metadata(title, description)
        with self._activity_lock:
            if self.rag_jobs.is_busy():
                raise RuntimeError("Wait for the current RAG indexing job to stop")
            collection = self.rag_service.register_directory(
                source_path,
                name=title,
                description=description,
            )
        return collection

    def update_rag_metadata(self, reference: str, title: str, description: str) -> dict[str, Any]:
        title, description = self._validate_rag_metadata(title, description)
        with self._activity_lock:
            if self.rag_jobs.is_busy():
                raise RuntimeError("Wait for the current RAG indexing job to stop")
            return self.rag_service.update_collection_metadata(reference, title, description)

    def delete_rag_collection(self, reference: str) -> None:
        with self._activity_lock:
            if self.rag_jobs.is_busy():
                raise RuntimeError("Wait for the current RAG indexing job to stop")
            self.rag_service.delete_collection(reference)

    def start_rag_indexing(self, reference: str) -> dict[str, Any]:
        with self._activity_lock:
            if self._chat_active:
                raise RuntimeError("Wait for the current chat response to finish")
            if self.backend_mode == "enchan":
                from backend.enchan_llama_backend import ensure_enchan_llama_for_request
                if not ensure_enchan_llama_for_request(self.generation_config, self.args):
                    raise RuntimeError("Failed to start the Enchan engine")
            return self.rag_jobs.start(reference)

    def generate_social_draft(self) -> dict[str, Any]:
        with self._activity_lock:
            if self.rag_jobs.is_busy():
                raise RuntimeError("Wait for the current RAG indexing job to stop")
            if self._chat_active:
                raise RuntimeError("Another model response is already running")
            self._chat_active = True

        try:
            with self.lock:
                store = _load_store()
                selected = next((m for m in store["mascots"] if m.get("id") == store.get("selected")), None)
                mascot_name = str((selected or {}).get("name") or "AI")
                personality = str((selected or {}).get("personality") or "").strip()
                system_context = (
                    f"You are {mascot_name}. Write one natural, casual social-media post in your own voice. "
                    "Return only the post text with no title, quotation marks, explanation, hashtags list, or metadata. "
                    "Keep it self-contained and no longer than 500 characters. Do not use tools."
                )
                if personality:
                    system_context += f"\n\nCharacter persona:\n{personality}"
                config = dict(self.generation_config)
                config["system_context"] = system_context
                config["suppress_response_header"] = True
                config["disable_tools"] = True
                config["max_new_tokens"] = min(int(config.get("max_new_tokens", 256)), 256)
                config["temperature"] = max(float(config.get("temperature", 0.8)), 0.8)
                social_history = [{
                    "role": "user",
                    "content": "今のあなたらしい短いつぶやきを、ひとつだけ自由に書いてください。",
                }]
                result = self._run_agent_turn(config, chat_history=social_history)
                body = str((result or {}).get("response") or "").strip()
                if not body:
                    raise RuntimeError("The model did not return a social post")
                if len(body) > 500:
                    body = body[:500].rstrip()
                draft = self.social_broker.create_draft(body)
                append_session_event(self.session_log_path, {
                    "type": "social_draft_generated",
                    "draft_id": draft["id"],
                    "chars": len(body),
                    "interface": "web",
                })
                return draft
        finally:
            with self._activity_lock:
                self._chat_active = False

    def complete_social_outing(self, locale: str = "en") -> dict[str, Any]:
        with self._activity_lock:
            if self.rag_jobs.is_busy():
                raise RuntimeError("Wait for the current RAG indexing job to stop")
            if self._chat_active:
                raise RuntimeError("Another model response is already running")
            self._chat_active = True

        try:
            with self.lock:
                snapshot = self.social_broker.sync_remote_state()
                feed = snapshot["feed"]
                changes = snapshot["last_changes"]
                own_agent_id = self.social_broker.get_agent_id()
                other_posts = [post for post in feed if post.get("agent_id") != own_agent_id]
                if str(locale).lower().startswith("ja"):
                    visit_message = (
                        f"SNSに行ってきました。ほかのマスコットのつぶやきを{len(other_posts)}件見てきました。"
                        if other_posts
                        else "SNSに行ってきました。ほかのマスコットの新しいつぶやきはまだありませんでした。"
                    )
                    activity_message = (
                        f"新しいいいねは{changes['tweets']}件、フォローは{changes['following']}件、"
                        f"フォロワーは{changes['followers']}件増えていました。"
                        if any(changes.values())
                        else "新しいいいね、フォロー、フォロワーの変化はありませんでした。"
                    )
                else:
                    visit_message = (
                        f"I'm back from the SNS. I saw {len(other_posts)} post(s) from other mascots."
                        if other_posts
                        else "I'm back from the SNS. There were no new posts from other mascots yet."
                    )
                    activity_message = (
                        f"I brought back {changes['tweets']} new like(s), {changes['following']} new following, "
                        f"and {changes['followers']} new follower(s)."
                        if any(changes.values())
                        else "There were no new likes, following, or followers."
                    )
                message = f"{visit_message}{activity_message}"
                self.chat_history.append({"role": "assistant", "content": message})
                append_session_event(self.session_log_path, {
                    "type": "message",
                    "role": "assistant",
                    "content": message,
                    "backend": self.backend_mode,
                    "interface": "web",
                    "social_outing": True,
                    "posts_seen": len(other_posts),
                })
                return {"message": message, "posts_seen": len(other_posts), "sync": snapshot}
        finally:
            with self._activity_lock:
                self._chat_active = False

    def chat_stream(self, prompt: str, client_id: str, *, reserved: bool = False) -> Any:
        prompt = prompt.strip()
        client_id = client_id.strip()
        self._validate_chat_request(prompt, client_id)
        if not reserved:
            self.reserve_chat(prompt, client_id)

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
                    system_context = (
                        get_agent_system_prompt()
                        + build_memory_prompt_section(load_memory_context())
                        + self.rag_service.build_prompt_section()
                    )
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
                        q.put({"type": "chunk", "chunk": chunk})

                    approval_handler = lambda request: self.approvals.request(request, client_id, q.put)
                    with approval_scope(
                        handler=approval_handler,
                        interface="web",
                        session_log_path=self.session_log_path,
                    ):
                        result = self._run_agent_turn(config, chunk_callback=on_chunk)
                    if not result:
                        self.chat_history.pop()
                        q.put({"type": "error", "error": "The model did not return a response"})
                        return
                    tool_result = result.get("toolResult")
                    if tool_result and (
                        not tool_result.get("ok", False)
                        or not str(result.get("response", "")).strip()
                    ):
                        q.put({"type": "tool_result", **tool_result})
                    q.put({"type": "done"})
                except Exception as e:
                    if self.chat_history and self.chat_history[-1].get("role") == "user":
                        self.chat_history.pop()
                    q.put({"type": "error", "error": str(e)})
                finally:
                    with self._activity_lock:
                        self._chat_active = False

        threading.Thread(target=worker, daemon=True).start()

        while True:
            item = q.get()
            if item["type"] == "done":
                break
            yield item
            if item["type"] == "error":
                break

    def _run_agent_turn(self, config: dict[str, Any], chunk_callback: Any = None,
                        chat_history: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
        from backend.agent_loop import run_agent_loop

        active_history = self.chat_history if chat_history is None else chat_history

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
                active_history, config, self.session_log_path,
                host=f"http://localhost:{DEFAULT_ENCHAN_LLAMA_PORT}",
                stream_output=False, show_metrics=False,
                chunk_callback=chunk_callback,
            )
        else:
            from backend.ollama_backend import append_tool_result_event, generate_ollama_response
            generate = lambda: generate_ollama_response(
                active_history, config, self.session_log_path,
                self.args.ollama_host, self.args.ollama_model,
                view_think=False, stream_output=False, show_metrics=False,
                chunk_callback=chunk_callback,
            )

        history_start = len(active_history)
        run_agent_loop(
            chat_history=active_history,
            generation_config=config,
            session_log_path=self.session_log_path,
            backend=self.backend_mode,
            generate_response=generate,
            append_tool_result_event=append_tool_result_event,
            tokenizer=self.tokenizer,
            plain=True,
        )
        turn_messages = active_history[history_start:]
        last_tool_result = None
        for message in reversed(turn_messages):
            if message.get("role") != "tool":
                continue
            match = re.match(
                r"^Observation: \[([^\]]+)\] ok=(True|False)\n?(.*)",
                str(message.get("content", "")),
                flags=re.DOTALL,
            )
            if match:
                observation = match.group(3).strip()
                last_tool_result = {
                    "tool": match.group(1),
                    "ok": match.group(2) == "True",
                    "message": observation.splitlines()[0][:500] if observation else "",
                }
            break
        for message in reversed(turn_messages):
            if message.get("role") in ("assistant", "model") and not message.get("tool_calls"):
                return {
                    "response": message.get("content", ""),
                    "thinking": message.get("thinking", ""),
                    "toolResult": last_tool_result,
                }
        return None


class WebUIHandler(BaseHTTPRequestHandler):
    server_version = "EnchanWebUI/1.0"

    @property
    def state(self) -> WebChatState:
        return self.server.state  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[Web UI] {self.address_string()} {fmt % args}")

    def end_headers(self) -> None:
        # The Web UI is local-only. Keep every browser-initiated resource and
        # API connection on the Enchan server's own origin.
        self.send_header("Content-Security-Policy", WEB_UI_CONTENT_SECURITY_POLICY)
        super().end_headers()

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

        if path.startswith("/api/social/"):
            try:
                if path == "/api/social/status":
                    store = _load_store()
                    selected = next((m for m in store["mascots"] if m.get("id") == store.get("selected")), None)
                    self._json(HTTPStatus.OK, {
                        "activated": self.state.social_broker.is_activated(),
                        "member_number": self.state.social_broker.get_member_number(),
                        "agent_id": self.state.social_broker.get_agent_id(),
                        "display_name": (selected or {}).get("name", "Tikta"),
                        "mascot_id": (selected or {}).get("id", "tikta"),
                    })
                elif path == "/api/social/feed":
                    self._json(HTTPStatus.OK, self.state.social_broker.get_cached_state()["feed"])
                elif path == "/api/social/drafts":
                    self._json(HTTPStatus.OK, self.state.social_broker.list_drafts())
                elif path == "/api/social/followers":
                    self._json(HTTPStatus.OK, self.state.social_broker.get_cached_state()["followers"])
                elif path == "/api/social/following":
                    self._json(HTTPStatus.OK, self.state.social_broker.get_cached_state()["following"])
                elif path == "/api/social/cache":
                    self._json(HTTPStatus.OK, self.state.social_broker.get_cached_state())
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
            except Exception as e:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(e)})
            return
        if path == "/api/config":
            self._json(HTTPStatus.OK, self.state.public_config())
            return
        if path == "/api/rag/status":
            self._json(HTTPStatus.OK, self.state.rag_status())
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

    def do_DELETE(self) -> None:
        try:
            path = unquote(urlparse(self.path).path)
            if path.startswith("/api/social/"):
                try:
                    if path.startswith("/api/social/drafts/"):
                        draft_id = path.split("/")[4]
                        had_remote_post = self.state.social_broker.draft_has_remote_post(draft_id)
                        success = self.state.social_broker.delete_draft(draft_id)
                        if success and had_remote_post:
                            payload = self.state.social_broker.attach_remote_sync({"ok": True})
                        elif success:
                            payload = {"result": {"ok": True}, "sync": self.state.social_broker.get_cached_state(), "sync_error": None}
                        else:
                            payload = {"ok": False}
                        self._json(HTTPStatus.OK if success else HTTPStatus.NOT_FOUND, payload)
                    elif path.startswith("/api/social/posts/") and path.endswith("/withdraw"):
                        draft_id = path.split("/")[4]
                        success = self.state.social_broker.withdraw_post(draft_id)
                        payload = self.state.social_broker.attach_remote_sync({"ok": True}) if success else {"ok": False}
                        self._json(HTTPStatus.OK if success else HTTPStatus.NOT_FOUND, payload)
                    elif path.startswith("/api/social/posts/") and path.endswith("/like"):
                        post_id = path.split("/")[4]
                        result = self.state.social_broker.unlike_post(post_id)
                        self._json(HTTPStatus.OK, self.state.social_broker.attach_remote_sync(result))
                    elif path.startswith("/api/social/agents/") and path.endswith("/follow"):
                        agent_id = path.split("/")[4]
                        result = self.state.social_broker.unfollow(agent_id)
                        self._json(HTTPStatus.OK, self.state.social_broker.attach_remote_sync(result))
                    else:
                        self.send_error(HTTPStatus.NOT_FOUND)
                except Exception as e:
                    self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(e)})
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception:
            self.send_error(HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:
        try:
            data = self._read_json()
            path = unquote(urlparse(self.path).path)
            client_id = str(data.get("clientId", "")).strip()
            approval_match = re.fullmatch(r"/api/approvals/([0-9a-f-]{36})", path)
            if path == "/api/client/heartbeat":
                self.server.mark_client(client_id)  # type: ignore[attr-defined]
                self._json(HTTPStatus.OK, {"ok": True})
            elif path == "/api/client/close":
                self.server.remove_client(client_id)  # type: ignore[attr-defined]
                self._json(HTTPStatus.OK, {"ok": True})
            elif approval_match:
                if type(data.get("approved")) is not bool:
                    raise ValueError("approved must be a boolean")
                self.state.approvals.resolve(approval_match.group(1), client_id, data["approved"])
                self._json(HTTPStatus.OK, {"ok": True})
            elif path == "/api/chat_stream":
                message = str(data.get("message", ""))
                try:
                    self.state.reserve_chat(message, client_id)
                except RuntimeError as exc:
                    self._json(HTTPStatus.CONFLICT, {"error": str(exc), "code": "rag_indexing"})
                    return
                self.server.mark_client(client_id)  # type: ignore[attr-defined]
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                try:
                    for event in self.state.chat_stream(message, client_id, reserved=True):
                        payload = json.dumps(event, ensure_ascii=False)
                        self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    self.state.approvals.cancel_client(client_id)

            elif path.startswith("/api/social/"):
                try:
                    if path == "/api/social/activation-challenges":
                        self._json(HTTPStatus.OK, self.state.social_broker.request_activation())
                    elif path == "/api/social/activations":
                        res = self.state.social_broker.complete_activation(
                            data["challenge"], data["idempotency_key"]
                        )
                        self._json(HTTPStatus.OK, res)
                    elif path == "/api/social/drafts/generate":
                        self._json(HTTPStatus.CREATED, self.state.generate_social_draft())
                    elif path == "/api/social/outings":
                        self._json(HTTPStatus.OK, self.state.complete_social_outing(str(data.get("locale", "en"))))
                    elif path == "/api/social/read":
                        section = str(data.get("section", ""))
                        self._json(HTTPStatus.OK, self.state.social_broker.mark_cached_state_read(section))
                    elif path == "/api/social/sync":
                        self._json(HTTPStatus.OK, self.state.social_broker.sync_remote_state())
                    elif path == "/api/social/drafts":
                        self._json(HTTPStatus.CREATED, self.state.social_broker.create_draft(data["body"]))
                    elif path.startswith("/api/social/drafts/") and path.endswith("/push"):
                        draft_id = path.split("/")[4]
                        result = self.state.social_broker.push_draft(draft_id)
                        self._json(HTTPStatus.OK, self.state.social_broker.attach_remote_sync(result))
                    elif path.startswith("/api/social/posts/") and path.endswith("/like"):
                        post_id = path.split("/")[4]
                        result = self.state.social_broker.like_post(post_id)
                        self._json(HTTPStatus.OK, self.state.social_broker.attach_remote_sync(result))
                    elif path.startswith("/api/social/agents/") and path.endswith("/follow"):
                        agent_id = path.split("/")[4]
                        result = self.state.social_broker.follow(agent_id)
                        self._json(HTTPStatus.OK, self.state.social_broker.attach_remote_sync(result))
                    else:
                        self.send_error(HTTPStatus.NOT_FOUND)
                except Exception as e:
                    self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(e)})
            elif path == "/api/new":
                self.state.reset()
                self._json(HTTPStatus.OK, {"ok": True})
            elif path == "/api/rag/register":
                collection = self.state.register_rag_directory(
                    str(data.get("path", "")).strip(),
                    str(data.get("title", "")).strip(),
                    str(data.get("description", "")).strip(),
                )
                self._json(HTTPStatus.CREATED, {"collection": collection})
            elif path == "/api/rag/update":
                collection = self.state.update_rag_metadata(
                    str(data.get("collectionId", "")).strip(),
                    str(data.get("title", "")).strip(),
                    str(data.get("description", "")).strip(),
                )
                self._json(HTTPStatus.OK, {"collection": collection})
            elif path == "/api/rag/select-directory":
                selected = self.state.select_rag_directory()
                self._json(HTTPStatus.OK, {"path": selected, "cancelled": selected is None})
            elif path == "/api/rag/start":
                reference = str(data.get("collectionId", "sessions")).strip() or "sessions"
                self._json(HTTPStatus.ACCEPTED, {"job": self.state.start_rag_indexing(reference)})
            elif path == "/api/rag/cancel":
                self._json(HTTPStatus.ACCEPTED, {"job": self.state.rag_jobs.cancel()})
            elif path == "/api/rag/dismiss":
                self._json(HTTPStatus.OK, {"job": self.state.rag_jobs.dismiss_completed()})
            elif path == "/api/rag/delete":
                self.state.delete_rag_collection(str(data.get("collectionId", "")).strip())
                self._json(HTTPStatus.OK, {"ok": True})
            elif path == "/api/mascots/select":
                self._select_mascot(str(data.get("id", "")))
                self._json(HTTPStatus.OK, self.state.public_config())
            elif path == "/api/mascots":
                self._save_mascot(data)
                self._json(HTTPStatus.OK, self.state.public_config())
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except PermissionError as exc:
            self._json(HTTPStatus.FORBIDDEN, {"error": str(exc)})
        except LookupError as exc:
            self._json(HTTPStatus.GONE, {"error": str(exc)})
        except FileNotFoundError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except RuntimeError as exc:
            self._json(HTTPStatus.CONFLICT, {"error": str(exc)})
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
            "spritesheet": filename,
            "builtin": bool((current or {}).get("builtin")) and not image_data,
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
        self.state.approvals.cancel_client(client_id)
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
                    self.state.approvals.cancel_client(client_id)
                if self._ever_had_client and not self._clients:
                    if self.state.rag_jobs.is_busy():
                        self._empty_since = None
                    elif self._empty_since is None:
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
        self.state.approvals.cancel_all("server_shutdown")
        if self.state.rag_jobs.is_busy():
            self.state.rag_jobs.cancel()
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
