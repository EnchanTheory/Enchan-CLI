"""Document chunking and persisted lexical index lifecycle."""

from __future__ import annotations

import bisect
import hashlib
from datetime import datetime, timezone
from typing import Any, Callable

from backend.rag.search import INDEX_VERSION, build_lexical_index
from backend.rag.store import RAGStore
from backend.rag.structure import STRUCTURE_VERSION, build_semantic_graph


ProgressCallback = Callable[[dict[str, Any]], None]


class RAGIndexCancelled(RuntimeError):
    """Raised after an in-progress structure checkpoint has been saved."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit_progress(
    callback: ProgressCallback | None,
    stage: str,
    current: int,
    total: int,
    percent: float,
    message: str,
    **details: Any,
) -> None:
    if callback is not None:
        callback({
            "stage": stage,
            "current": current,
            "total": total,
            "percent": max(0.0, min(100.0, percent)),
            "message": message,
            **details,
        })


def _chunk_id(source_path: str, line_start: int, text: str) -> str:
    value = f"{source_path}\0{line_start}\0{text}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


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


STRUCTURE_CHARS = 12_000
SEARCH_CHARS = 1_500
SEARCH_STRIDE = 500
STRUCTURE_CACHE_CHECKPOINT_INTERVAL = 25


def _offset_chunk(
    document: dict[str, Any],
    text: str,
    char_start: int,
    char_end: int,
    line_offsets: list[int],
    *,
    structure_id: str | None = None,
) -> dict[str, Any]:
    source_path = document["source_path"]
    line_start = bisect.bisect_right(line_offsets, char_start)
    line_end = bisect.bisect_right(line_offsets, max(char_start, char_end - 1))
    identity = f"{source_path}\0{char_start}\0{text}"
    chunk_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    metadata = {
        "source_path": source_path,
        "title": document.get("title"),
        "heading": document.get("title"),
        "line_start": line_start,
        "line_end": line_end,
        "char_start": char_start,
        "char_end": char_end,
        "mtime_ns": document.get("mtime_ns"),
    }
    if structure_id:
        metadata["structure_id"] = structure_id
    return {"id": chunk_id, "text": text, "metadata": metadata}


def hierarchical_chunks(document: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build SATODW-style 12k structure parents and 1500/500 search children."""
    text = document["text"]
    if not text.strip():
        return [], []
    if document.get("pre_chunked"):
        child = _make_chunk(document, text.strip(), 1, text.count("\n") + 1, document.get("title"))
        child["metadata"]["structure_id"] = child["id"]
        return [dict(child)], [child]

    line_offsets = [0]
    line_offsets.extend(match.end() for match in __import__("re").finditer(r"\n", text))
    parents: list[dict[str, Any]] = []
    for start in range(0, len(text), STRUCTURE_CHARS):
        segment = text[start:start + STRUCTURE_CHARS].strip()
        if not segment:
            continue
        parents.append(_offset_chunk(document, segment, start, min(len(text), start + STRUCTURE_CHARS), line_offsets))

    children: list[dict[str, Any]] = []
    parent_by_slot = {int(parent["metadata"]["char_start"]) // STRUCTURE_CHARS: parent["id"] for parent in parents}
    for start in range(0, len(text), SEARCH_STRIDE):
        segment = text[start:start + SEARCH_CHARS].strip()
        if not segment:
            continue
        structure_id = parent_by_slot.get(start // STRUCTURE_CHARS)
        children.append(
            _offset_chunk(
                document,
                segment,
                start,
                min(len(text), start + SEARCH_CHARS),
                line_offsets,
                structure_id=structure_id,
            )
        )
    return parents, children


class RAGIndexer:
    def __init__(self, store: RAGStore):
        self.store = store

    def inspect(self, collection: dict[str, Any], source) -> dict[str, Any]:
        """Compare source state with the persisted index without changing either."""
        collection_id = collection["id"]
        snapshot = source.snapshot()
        previous = self.store.load_json(collection_id, "file_state.json", {})
        has_index = (self.store.collection_dir(collection_id) / "lexical_index.json").exists()
        index_compatible = int(collection.get("index_version", 0)) == INDEX_VERSION
        source_missing = bool(snapshot.get("source_missing"))
        stale = has_index and not source_missing and (snapshot != previous or not index_compatible)
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
            "indexed": has_index and index_compatible,
            "source_missing": source_missing,
            "file_count": len(snapshot.get("files", {})),
            "indexed_file_count": int(collection.get("indexed_file_count", 0)),
            "chunk_count": int(collection.get("indexed_chunk_count", 0)),
        }
    def rebuild(
        self,
        collection: dict[str, Any],
        source,
        *,
        force: bool = False,
        progress: ProgressCallback | None = None,
        analyzer: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        collection_id = collection["id"]
        _emit_progress(progress, "scan", 0, 1, 0.0, "Scanning source files")
        snapshot = source.snapshot()
        file_total = len(snapshot.get("files", {}))
        _emit_progress(progress, "scan", file_total, file_total, 5.0, f"Found {file_total} files")
        previous = self.store.load_json(collection_id, "file_state.json", {})
        has_index = (self.store.collection_dir(collection_id) / "lexical_index.json").exists()
        index_compatible = int(collection.get("index_version", 0)) == INDEX_VERSION
        if snapshot.get("source_missing"):
            collection = dict(collection)
            collection["status"] = "source_missing"
            self.store.save_collection(collection)
            return {"changed": False, "source_missing": True, "file_count": collection.get("indexed_file_count", 0), "chunk_count": collection.get("indexed_chunk_count", 0), "diagnostics": []}
        if not force and snapshot == previous and has_index and index_compatible:
            return {"changed": False, "source_missing": False, "file_count": len(snapshot.get("files", {})), "chunk_count": collection.get("indexed_chunk_count", 0), "diagnostics": []}

        def on_load(current: int, total: int, name: str) -> None:
            ratio = current / max(1, total)
            _emit_progress(progress, "load", current, total, 5.0 + ratio * 15.0, f"Reading {name}")

        documents, diagnostics = source.load_documents(progress=on_load)
        structure_units: list[dict[str, Any]] = []
        chunks: list[dict[str, Any]] = []
        document_total = len(documents)
        for position, document in enumerate(documents, 1):
            parents, children = hierarchical_chunks(document)
            structure_units.extend(parents)
            chunks.extend(children)
            ratio = position / max(1, document_total)
            _emit_progress(
                progress,
                "chunk",
                position,
                document_total,
                20.0 + ratio * 25.0,
                f"Chunking {document.get('source_path', '')}",
            )

        cached_payload = self.store.load_json(collection_id, "structure_cache.json", {})
        cached = cached_payload.get("chunks", {}) if cached_payload.get("version") == STRUCTURE_VERSION else {}
        structures: dict[str, Any] = {}
        analyzed_count = 0
        analysis_attempted_count = 0
        analysis_failed_count = 0
        reused_count = 0
        pending_cache_updates = 0
        analysis_total = sum(
            1 for unit in structure_units
            if analyzer is not None and not (isinstance(cached.get(unit["id"]), dict) and cached.get(unit["id"]))
        )

        def save_structure_checkpoint() -> None:
            self.store.save_json(
                collection_id,
                "structure_cache.json",
                {"version": STRUCTURE_VERSION, "chunks": {**cached, **structures}},
            )

        def stop_if_requested(position: int) -> None:
            if should_cancel is None or not should_cancel():
                return
            save_structure_checkpoint()
            _emit_progress(
                progress,
                "interrupted",
                position,
                len(structure_units),
                45.0 + (position / max(1, len(structure_units))) * 35.0,
                "Indexing interrupted; structure checkpoint saved",
                analysis_current=analysis_attempted_count,
                analysis_total=analysis_total,
                reused_count=reused_count,
                failed_count=analysis_failed_count,
            )
            raise RAGIndexCancelled("RAG indexing interrupted after saving a structure checkpoint")

        for position, unit in enumerate(structure_units, 1):
            stop_if_requested(position - 1)
            chunk_id = unit["id"]
            structure = cached.get(chunk_id)
            if isinstance(structure, dict) and structure:
                reused_count += 1
            elif analyzer is not None:
                analysis_attempted_count += 1
                try:
                    structure = analyzer(unit)
                    analyzed_count += 1
                except Exception as exc:
                    analysis_failed_count += 1
                    diagnostics.append(f"Structure analysis failed for {chunk_id}: {exc}")
                    structure = {}
            else:
                structure = {}
            unit["structure"] = structure
            if structure:
                structures[chunk_id] = structure
                if analyzer is not None and chunk_id not in cached:
                    pending_cache_updates += 1
                    if pending_cache_updates >= STRUCTURE_CACHE_CHECKPOINT_INTERVAL:
                        save_structure_checkpoint()
                        pending_cache_updates = 0
            ratio = position / max(1, len(structure_units))
            _emit_progress(
                progress,
                "structure",
                position,
                len(structure_units),
                45.0 + ratio * 35.0,
                f"Structuring parent chunks ({position}/{len(structure_units)})",
                analysis_current=analysis_attempted_count,
                analysis_total=analysis_total,
                reused_count=reused_count,
                failed_count=analysis_failed_count,
            )
            stop_if_requested(position)

        for chunk in chunks:
            structure_id = chunk.get("metadata", {}).get("structure_id")
            chunk["structure"] = structures.get(structure_id, {})

        semantic_graph = build_semantic_graph(chunks)

        def on_index(current: int, total: int) -> None:
            ratio = current / max(1, total)
            _emit_progress(
                progress,
                "index",
                current,
                total,
                80.0 + ratio * 12.0,
                f"Indexing multilingual features ({current}/{total} chunks)",
            )

        lexical_index = build_lexical_index(chunks, progress=on_index)

        _emit_progress(progress, "save", 0, 1, 92.0, "Saving persistent index")
        self.store.save_chunks(collection_id, chunks)
        self.store.save_json(collection_id, "lexical_index.json", lexical_index)
        self.store.save_json(collection_id, "structure_cache.json", {"version": STRUCTURE_VERSION, "chunks": structures})
        self.store.save_json(collection_id, "semantic_graph.json", semantic_graph)

        self.store.save_json(collection_id, "file_state.json", snapshot)
        collection = dict(collection)
        collection.update({
            "status": "ready",
            "last_index_update": _now_iso(),
            "indexed_file_count": len(snapshot.get("files", {})),
            "indexed_chunk_count": len(chunks),
            "index_version": INDEX_VERSION,
            "structure_version": STRUCTURE_VERSION,
            "structured_chunk_count": sum(1 for value in structures.values() if value),
            "structure_unit_count": len(structure_units),
        })
        self.store.save_collection(collection)
        _emit_progress(progress, "done", 1, 1, 100.0, f"Indexed {len(chunks)} chunks")
        return {"changed": True, "source_missing": False, "file_count": collection["indexed_file_count"], "chunk_count": len(chunks), "structure_unit_count": len(structure_units), "analysis_attempted_count": analysis_attempted_count, "analyzed_count": analyzed_count, "analysis_failed_count": analysis_failed_count, "reused_count": reused_count, "diagnostics": diagnostics}
