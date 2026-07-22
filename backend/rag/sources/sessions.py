"""Enchan session JSONL source adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from backend.rag.sources.directory import DirectorySource


SESSION_SOURCE_VERSION = 2
SOCIAL_METADATA_KEYS = (
    "social_memory", "social_outing", "social_activity", "mascot_id",
    "mascot_name", "post_id", "draft_id", "post_status", "post_author",
    "agent_id", "other_mascot_name", "social_action_source",
)


class SessionSource(DirectorySource):
    source_type = "sessions"

    def __init__(self, collection: dict[str, Any]):
        configured = dict(collection)
        configured["extensions"] = [".jsonl"]
        super().__init__(configured)

    def snapshot(self) -> dict[str, Any]:
        snapshot = super().snapshot()
        snapshot["adapter_version"] = SESSION_SOURCE_VERSION
        return snapshot

    def load_documents(
        self,
        progress: Callable[[int, int, str], None] | None = None,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        documents: list[dict[str, Any]] = []
        diagnostics: list[str] = []
        files = list(self.iter_files())
        total = len(files)
        for position, (path, relative, stat) in enumerate(files, 1):
            if progress is not None:
                progress(position, total, relative.as_posix())
            messages = []
            try:
                with path.open("r", encoding="utf-8", errors="replace") as handle:
                    for line_number, line in enumerate(handle, 1):
                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if event.get("type") != "message":
                            continue
                        role = event.get("role")
                        content = event.get("content")
                        if role == "model":
                            role = "assistant"
                        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                            message = {
                                "role": role, "content": content.strip(),
                                "ts": event.get("ts"), "line_number": line_number,
                            }
                            if event.get("social_memory") or event.get("social_outing") or event.get("social_activity"):
                                message["social_event"] = {
                                    key: event.get(key)
                                    for key in SOCIAL_METADATA_KEYS
                                    if event.get(key) not in (None, "", False)
                                }
                            messages.append(message)
            except OSError as exc:
                diagnostics.append(f"Skipped {relative}: {exc}")
                continue

            window: list[dict[str, Any]] = []
            turn = 0
            for message in messages:
                if message.get("social_event"):
                    if window:
                        documents.append(self._window_document(relative, path, stat, turn, window))
                        turn += 1
                        window = []
                    documents.append(self._social_document(relative, path, stat, turn, message))
                    turn += 1
                    continue
                if message["role"] == "user" and window:
                    documents.append(self._window_document(relative, path, stat, turn, window))
                    turn += 1
                    window = []
                window.append(message)
            if window:
                documents.append(self._window_document(relative, path, stat, turn, window))
        return documents, diagnostics

    @staticmethod
    def _social_document(relative: Path, path: Path, stat, turn: int, message: dict[str, Any]) -> dict[str, Any]:
        social = dict(message.get("social_event") or {})
        search_terms = ["SNS", "social activity memory"]
        search_terms.extend(social)
        search_terms.extend(str(value) for value in social.values() if not isinstance(value, bool))
        return {
            "source_path": relative.as_posix(),
            "title": path.stem,
            "text": f"{message['role'].title()}:\n{message['content']}",
            "mtime_ns": stat.st_mtime_ns,
            "timestamp": message.get("ts"),
            "turn": turn,
            "line_start": message.get("line_number", 1),
            "pre_chunked": True,
            "search_terms": " ".join(search_terms),
            **social,
        }

    @staticmethod
    def _window_document(relative: Path, path: Path, stat, turn: int, messages: list[dict[str, Any]]) -> dict[str, Any]:
        text = "\n\n".join(f"{item['role'].title()}:\n{item['content']}" for item in messages)
        timestamp = next((item.get("ts") for item in messages if item.get("ts")), None)
        return {
            "source_path": relative.as_posix(),
            "title": path.stem,
            "text": text,
            "mtime_ns": stat.st_mtime_ns,
            "timestamp": timestamp,
            "turn": turn,
            "pre_chunked": True,
        }
