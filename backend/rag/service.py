"""Reusable local RAG service shared by CUI, tools, and future UIs."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from backend.rag.indexer import RAGIndexer
from backend.rag.search import retrieve_candidates, select_candidates
from backend.rag.sources import DirectorySource, SessionSource
from backend.rag.store import RAGStore, collection_id_for, normalize_source_path


class RAGService:
    def __init__(self, store_root: str | Path | None = None, selector: Callable[..., list[int]] | None = None):
        self.store = RAGStore(store_root)
        self.indexer = RAGIndexer(self.store)
        self.selector = selector

    def register_directory(self, source_path: str | Path, name: str | None = None) -> dict[str, Any]:
        path = Path(source_path).expanduser().resolve(strict=False)
        if not path.exists() or not path.is_dir():
            raise FileNotFoundError(f"RAG source directory not found: {path}")
        collection_id = collection_id_for("directory", path)
        existing = self.store.load_collection(collection_id) or {}
        collection = {
            **existing,
            "id": collection_id,
            "name": name or existing.get("name") or path.name,
            "source_type": "directory",
            "source_path": normalize_source_path(path),
            "enabled": existing.get("enabled", True),
            "extensions": existing.get("extensions", [".txt", ".md", ".jsonl"]),
            "exclude_paths": existing.get("exclude_paths", [".git", ".venv", "__pycache__", "node_modules"]),
            "rag_store_path": normalize_source_path(self.store.root),
            "chunk_chars": existing.get("chunk_chars", 1600),
            "chunk_overlap": existing.get("chunk_overlap", 200),
            "candidate_count": existing.get("candidate_count", 20),
            "selection_count": existing.get("selection_count", 6),
            "status": existing.get("status", "registered"),
        }
        self.store.save_collection(collection)
        return collection

    def ensure_session_collection(self, source_path: str | Path | None = None) -> dict[str, Any]:
        if source_path is None:
            from backend.session_log import SESSION_LOG_DIR
            source_path = SESSION_LOG_DIR
        path = Path(source_path).expanduser().resolve(strict=False)
        collection_id = collection_id_for("sessions", path)
        existing = self.store.load_collection(collection_id) or {}
        collection = {
            **existing,
            "id": collection_id,
            "name": "Enchan Sessions",
            "source_type": "sessions",
            "source_path": normalize_source_path(path),
            "enabled": True,
            "extensions": [".jsonl"],
            "exclude_paths": [],
            "rag_store_path": normalize_source_path(self.store.root),
            "chunk_chars": 4000,
            "chunk_overlap": 0,
            "candidate_count": existing.get("candidate_count", 20),
            "selection_count": existing.get("selection_count", 6),
            "status": existing.get("status", "registered"),
        }
        self.store.save_collection(collection)
        return collection

    def list_collections(self) -> list[dict[str, Any]]:
        return self.store.list_collections()

    def collection_status(self, reference: str) -> dict[str, Any]:
        collection = self.resolve_collection(reference)
        return {**collection, **self.indexer.inspect(collection, self._source_for(collection))}

    def list_collection_statuses(self) -> list[dict[str, Any]]:
        return [
            {**collection, **self.indexer.inspect(collection, self._source_for(collection))}
            for collection in self.store.list_collections()
        ]

    def resolve_collection(self, reference: str) -> dict[str, Any]:
        collection = self.store.resolve_collection(reference)
        if collection is None:
            raise KeyError(f"RAG collection not found: {reference}")
        return collection

    def _source_for(self, collection: dict[str, Any]):
        if collection.get("source_type") == "sessions":
            return SessionSource(collection)
        if collection.get("source_type") == "directory":
            return DirectorySource(collection)
        raise ValueError(f"Unsupported RAG source type: {collection.get('source_type')}")

    def rebuild(self, reference: str, *, force: bool = False) -> dict[str, Any]:
        collection = self.resolve_collection(reference)
        return self.indexer.rebuild(collection, self._source_for(collection), force=force)

    def search(
        self,
        reference: str,
        query: str,
        *,
        candidate_count: int | None = None,
        selection_count: int | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        collection = self.resolve_collection(reference)
        if not collection.get("enabled", True):
            raise RuntimeError(f"RAG collection is disabled: {collection.get('name')}")
        index_state = self.indexer.inspect(collection, self._source_for(collection))
        if not index_state["indexed"]:
            raise RuntimeError(
                f"RAG collection is not indexed: {collection.get('name')}. "
                f"Run /rag rebuild {collection['id']} first."
            )
        chunks = self.store.load_chunks(collection["id"])
        index = self.store.load_json(collection["id"], "lexical_index.json", {})
        candidate_limit = max(1, min(int(candidate_count or collection.get("candidate_count", 20)), 100))
        selection_limit = max(1, min(int(selection_count or collection.get("selection_count", 6)), candidate_limit))
        candidates = retrieve_candidates(query, chunks, index, candidate_limit)
        selected, method = select_candidates(query, candidates, selection_limit, index=index, selector=self.selector)
        return {
            "collection": {"id": collection["id"], "name": collection["name"], "source_type": collection["source_type"]},
            "query": query,
            "candidate_count": len(candidates),
            "selected_count": len(selected),
            "selection_method": method,
            "index_status": index_state["status"],
            "update_available": index_state["stale"],
            "source_missing": index_state["source_missing"],
            "elapsed_seconds": time.perf_counter() - started,
            "results": selected,
        }


_DEFAULT_SERVICE: RAGService | None = None


def get_default_service() -> RAGService:
    global _DEFAULT_SERVICE
    if _DEFAULT_SERVICE is None:
        _DEFAULT_SERVICE = RAGService()
        _DEFAULT_SERVICE.ensure_session_collection()
    return _DEFAULT_SERVICE
