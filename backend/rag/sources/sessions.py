"""Enchan session JSONL source adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.rag.sources.directory import DirectorySource


class SessionSource(DirectorySource):
    source_type = "sessions"

    def __init__(self, collection: dict[str, Any]):
        configured = dict(collection)
        configured["extensions"] = [".jsonl"]
        super().__init__(configured)

    def load_documents(self) -> tuple[list[dict[str, Any]], list[str]]:
        documents: list[dict[str, Any]] = []
        diagnostics: list[str] = []
        for path, relative, stat in self.iter_files():
            messages = []
            try:
                with path.open("r", encoding="utf-8", errors="replace") as handle:
                    for line in handle:
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
                            messages.append({"role": role, "content": content.strip(), "ts": event.get("ts")})
            except OSError as exc:
                diagnostics.append(f"Skipped {relative}: {exc}")
                continue

            window: list[dict[str, Any]] = []
            turn = 0
            for message in messages:
                if message["role"] == "user" and window:
                    documents.append(self._window_document(relative, path, stat, turn, window))
                    turn += 1
                    window = []
                window.append(message)
            if window:
                documents.append(self._window_document(relative, path, stat, turn, window))
        return documents, diagnostics

    @staticmethod
    def _window_document(relative: Path, path: Path, stat, turn: int, messages: list[dict[str, Any]]) -> dict[str, Any]:
        text = "\n\n".join(f"{item['role'].title()}:\n{item['content']}" for item in messages)
        timestamp = next((item.get("ts") for item in messages if item.get("ts")), None)
        return {
            "source_path": relative.as_posix(),
            "absolute_path": str(path),
            "title": path.stem,
            "text": text,
            "mtime_ns": stat.st_mtime_ns,
            "timestamp": timestamp,
            "turn": turn,
            "pre_chunked": True,
        }
