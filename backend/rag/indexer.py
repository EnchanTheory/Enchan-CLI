"""Document chunking and persisted lexical index lifecycle."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from backend.rag.search import build_lexical_index
from backend.rag.store import RAGStore


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _chunk_id(source_path: str, line_start: int, text: str) -> str:
    value = f"{source_path}\0{line_start}\0{text}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def chunk_document(document: dict[str, Any], target_chars: int, overlap_chars: int) -> list[dict[str, Any]]:
    text = document["text"].strip()
    if not text:
        return []
    if document.get("pre_chunked"):
        return [_make_chunk(document, text, 1, text.count("\n") + 1, document.get("title"))]

    lines = text.splitlines()
    chunks: list[dict[str, Any]] = []
    start = 0
    while start < len(lines):
        if len(lines[start]) > target_chars:
            raw_line = lines[start]
            step = max(1, target_chars - overlap_chars)
            offset = 0
            while offset < len(raw_line):
                segment = raw_line[offset:offset + target_chars].strip()
                if segment:
                    chunks.append(_make_chunk(document, segment, start + 1, start + 1, document.get("title")))
                if offset + target_chars >= len(raw_line):
                    break
                offset += step
            start += 1
            continue
        length = 0
        end = start
        heading = document.get("title")
        while end < len(lines):
            line = lines[end]
            if line.lstrip().startswith("#"):
                heading = line.lstrip("# ").strip() or heading
            added = len(line) + 1
            if end > start and length + added > target_chars:
                break
            length += added
            end += 1
        if end == start:
            end += 1
        chunk_text = "\n".join(lines[start:end]).strip()
        if chunk_text:
            chunks.append(_make_chunk(document, chunk_text, start + 1, end, heading))
        if end >= len(lines):
            break
        overlap_lines = 0
        overlap_length = 0
        for index in range(end - 1, start - 1, -1):
            overlap_length += len(lines[index]) + 1
            if overlap_length > overlap_chars:
                break
            overlap_lines += 1
        start = max(start + 1, end - overlap_lines)
    return chunks


def _make_chunk(document: dict[str, Any], text: str, line_start: int, line_end: int, heading: str | None) -> dict[str, Any]:
    source_path = document["source_path"]
    metadata = {
        "source_path": source_path,
        "title": document.get("title"),
        "heading": heading,
        "line_start": line_start,
        "line_end": line_end,
        "mtime_ns": document.get("mtime_ns"),
    }
    for key in ("timestamp", "turn"):
        if document.get(key) is not None:
            metadata[key] = document[key]
    return {"id": _chunk_id(source_path, line_start, text), "text": text, "metadata": metadata}


class RAGIndexer:
    def __init__(self, store: RAGStore):
        self.store = store

    def inspect(self, collection: dict[str, Any], source) -> dict[str, Any]:
        """Compare source state with the persisted index without changing either."""
        collection_id = collection["id"]
        snapshot = source.snapshot()
        previous = self.store.load_json(collection_id, "file_state.json", {})
        has_index = (self.store.collection_dir(collection_id) / "lexical_index.json").exists()
        source_missing = bool(snapshot.get("source_missing"))
        stale = has_index and not source_missing and snapshot != previous
        if source_missing:
            status = "source_missing"
        elif not has_index:
            status = "registered"
        elif stale:
            status = "stale"
        else:
            status = "ready"
        return {
            "status": status,
            "stale": stale,
            "indexed": has_index,
            "source_missing": source_missing,
            "file_count": len(snapshot.get("files", {})),
            "indexed_file_count": int(collection.get("indexed_file_count", 0)),
            "chunk_count": int(collection.get("indexed_chunk_count", 0)),
        }
    def rebuild(self, collection: dict[str, Any], source, *, force: bool = False) -> dict[str, Any]:
        collection_id = collection["id"]
        snapshot = source.snapshot()
        previous = self.store.load_json(collection_id, "file_state.json", {})
        has_index = (self.store.collection_dir(collection_id) / "lexical_index.json").exists()
        if snapshot.get("source_missing"):
            collection = dict(collection)
            collection["status"] = "source_missing"
            self.store.save_collection(collection)
            return {"changed": False, "source_missing": True, "file_count": collection.get("indexed_file_count", 0), "chunk_count": collection.get("indexed_chunk_count", 0), "diagnostics": []}
        if not force and snapshot == previous and has_index:
            return {"changed": False, "source_missing": False, "file_count": len(snapshot.get("files", {})), "chunk_count": collection.get("indexed_chunk_count", 0), "diagnostics": []}

        documents, diagnostics = source.load_documents()
        chunks: list[dict[str, Any]] = []
        target_chars = max(300, int(collection.get("chunk_chars", 1600)))
        overlap_chars = max(0, min(int(collection.get("chunk_overlap", 200)), target_chars // 2))
        for document in documents:
            chunks.extend(chunk_document(document, target_chars, overlap_chars))
        lexical_index = build_lexical_index(chunks)

        self.store.save_chunks(collection_id, chunks)
        self.store.save_json(collection_id, "lexical_index.json", lexical_index)
        self.store.save_json(collection_id, "file_state.json", snapshot)
        collection = dict(collection)
        collection.update({
            "status": "ready",
            "last_index_update": _now_iso(),
            "indexed_file_count": len(snapshot.get("files", {})),
            "indexed_chunk_count": len(chunks),
        })
        self.store.save_collection(collection)
        return {"changed": True, "source_missing": False, "file_count": collection["indexed_file_count"], "chunk_count": len(chunks), "diagnostics": diagnostics}
