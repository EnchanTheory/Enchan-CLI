"""Persistent collection storage for local RAG data."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any


STORE_VERSION = 1


def normalize_source_path(path: str | Path) -> str:
    resolved = Path(path).expanduser().resolve(strict=False)
    return os.path.normcase(os.path.normpath(str(resolved)))


def collection_id_for(source_type: str, source_path: str | Path) -> str:
    identity = f"{source_type}\0{normalize_source_path(source_path)}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temp, path)


class RAGStore:
    def __init__(self, root: str | Path | None = None):
        configured = root or os.environ.get("ENCHAN_RAG_HOME")
        self.root = Path(configured).expanduser() if configured else Path.home() / ".enchan" / "rag"
        self.collections_dir = self.root / "collections"
        self._json_cache: dict[tuple[str, str], tuple[int, int, Any]] = {}
        self._chunks_cache: dict[str, tuple[int, int, list[dict[str, Any]]]] = {}

    def collection_dir(self, collection_id: str) -> Path:
        return self.collections_dir / collection_id

    def metadata_path(self, collection_id: str) -> Path:
        return self.collection_dir(collection_id) / "collection.json"

    def save_json(self, collection_id: str, filename: str, payload: Any) -> None:
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        path = self.collection_dir(collection_id) / filename
        _atomic_write_text(path, text)
        stat = path.stat()
        self._json_cache[(collection_id, filename)] = (stat.st_mtime_ns, stat.st_size, payload)

    def load_json(self, collection_id: str, filename: str, default: Any = None) -> Any:
        path = self.collection_dir(collection_id) / filename
        if not path.exists():
            return default
        try:
            stat = path.stat()
        except OSError:
            return default
        cached = self._json_cache.get((collection_id, filename))
        if cached and cached[0] == stat.st_mtime_ns and cached[1] == stat.st_size:
            return cached[2]
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        self._json_cache[(collection_id, filename)] = (stat.st_mtime_ns, stat.st_size, payload)
        return payload

    def save_collection(self, collection: dict[str, Any]) -> None:
        collection = dict(collection)
        collection["store_version"] = STORE_VERSION
        self.save_json(collection["id"], "collection.json", collection)

    def load_collection(self, collection_id: str) -> dict[str, Any] | None:
        data = self.load_json(collection_id, "collection.json")
        return data if isinstance(data, dict) else None

    def delete_collection(self, collection_id: str) -> None:
        target = self.collection_dir(collection_id).resolve(strict=False)
        root = self.collections_dir.resolve(strict=False)
        if target.parent != root:
            raise ValueError("Invalid RAG collection path")
        if target.exists():
            shutil.rmtree(target)
        self._json_cache = {key: value for key, value in self._json_cache.items() if key[0] != collection_id}
        self._chunks_cache.pop(collection_id, None)

    def list_collections(self) -> list[dict[str, Any]]:
        if not self.collections_dir.exists():
            return []
        collections = []
        for path in sorted(self.collections_dir.glob("*/collection.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict):
                collections.append(data)
        return sorted(collections, key=lambda item: (str(item.get("name", "")).lower(), item.get("id", "")))

    def resolve_collection(self, reference: str) -> dict[str, Any] | None:
        normalized = reference.strip().lower()
        collections = self.list_collections()
        for collection in collections:
            if normalized in {
                str(collection.get("id", "")).lower(),
                str(collection.get("name", "")).lower(),
            }:
                return collection
            if normalized in {"session", "sessions"} and collection.get("source_type") == "sessions":
                return collection
        prefix_matches = [item for item in collections if str(item.get("id", "")).lower().startswith(normalized)]
        return prefix_matches[0] if len(prefix_matches) == 1 else None

    def save_chunks(self, collection_id: str, chunks: list[dict[str, Any]]) -> None:
        text = "".join(json.dumps(chunk, ensure_ascii=False, sort_keys=True) + "\n" for chunk in chunks)
        path = self.collection_dir(collection_id) / "chunks.jsonl"
        _atomic_write_text(path, text)
        stat = path.stat()
        self._chunks_cache[collection_id] = (stat.st_mtime_ns, stat.st_size, chunks)

    def load_chunks(self, collection_id: str) -> list[dict[str, Any]]:
        path = self.collection_dir(collection_id) / "chunks.jsonl"
        if not path.exists():
            return []
        try:
            stat = path.stat()
        except OSError:
            return []
        cached = self._chunks_cache.get(collection_id)
        if cached and cached[0] == stat.st_mtime_ns and cached[1] == stat.st_size:
            return cached[2]
        chunks = []
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    chunks.append(item)
        self._chunks_cache[collection_id] = (stat.st_mtime_ns, stat.st_size, chunks)
        return chunks
