"""Background RAG indexing lifecycle for interactive interfaces."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

from backend.rag.indexer import RAGIndexCancelled
from backend.rag.service import RAGService
from backend.rag.structure import LocalStructureAnalyzer


ACTIVE_STATES = {"running", "stopping"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _idle_status() -> dict[str, Any]:
    return {
        "state": "idle",
        "collectionId": None,
        "stage": "idle",
        "message": "",
        "messageKey": "",
        "messageValues": {},
        "current": 0,
        "total": 0,
        "percent": 0.0,
        "elapsedSeconds": 0.0,
        "etaSeconds": None,
        "analysisCurrent": 0,
        "analysisTotal": 0,
        "reusedCount": 0,
        "failedCount": 0,
        "canResume": False,
    }


class RAGIndexJobManager:
    """Run one local-model indexing job at a time and persist resumable state."""

    def __init__(self, service: RAGService, generation_config: dict[str, Any]) -> None:
        self.service = service
        self.generation_config = generation_config
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None
        self._started = 0.0
        self._status: dict[str, Any] = _idle_status()
        self._restore_interrupted_job()

    def _restore_interrupted_job(self) -> None:
        restored: list[dict[str, Any]] = []
        for collection in self.service.list_collections():
            job = self.service.store.load_json(collection["id"], "index_job.json", {})
            if not isinstance(job, dict) or not job.get("state") or job.get("dismissed"):
                continue
            if job.get("state") in ACTIVE_STATES:
                job = {**job, "state": "interrupted", "stage": "interrupted", "canResume": True,
                       "message": "Previous indexing process ended before completion",
                       "messageKey": "rag.progress.previousInterrupted", "messageValues": {}}
                self.service.store.save_json(collection["id"], "index_job.json", job)
            restored.append(job)
        if restored:
            restored.sort(key=lambda item: str(item.get("updatedAt", "")))
            self._status.update(restored[-1])

    def is_busy(self) -> bool:
        with self._lock:
            return self._status.get("state") in ACTIVE_STATES

    def status(self) -> dict[str, Any]:
        with self._lock:
            result = dict(self._status)
            if result.get("state") in ACTIVE_STATES:
                result["elapsedSeconds"] = max(0.0, time.monotonic() - self._started)
            return result

    def collection_job(self, collection_id: str) -> dict[str, Any]:
        with self._lock:
            if self._status.get("collectionId") == collection_id:
                return self.status_unlocked()
        job = self.service.store.load_json(collection_id, "index_job.json", {})
        return job if isinstance(job, dict) else {}

    def status_unlocked(self) -> dict[str, Any]:
        result = dict(self._status)
        if result.get("state") in ACTIVE_STATES:
            result["elapsedSeconds"] = max(0.0, time.monotonic() - self._started)
        return result

    def start(self, reference: str) -> dict[str, Any]:
        collection = self.service.resolve_collection(reference)
        with self._lock:
            if self._status.get("state") in ACTIVE_STATES:
                raise RuntimeError("RAG indexing is already running")
            self._cancel.clear()
            self._started = time.monotonic()
            self._status = {
                "state": "running",
                "collectionId": collection["id"],
                "collectionName": collection["name"],
                "stage": "starting",
                "message": "Preparing RAG indexing",
                "messageKey": "rag.progress.preparing",
                "messageValues": {},
                "current": 0,
                "total": 0,
                "percent": 0.0,
                "elapsedSeconds": 0.0,
                "etaSeconds": None,
                "analysisCurrent": 0,
                "analysisTotal": 0,
                "reusedCount": 0,
                "failedCount": 0,
                "canResume": False,
                "startedAt": _now_iso(),
                "updatedAt": _now_iso(),
            }
            self._persist_unlocked()
            self._thread = threading.Thread(
                target=self._run,
                args=(collection["id"],),
                name="enchan-rag-indexer",
                daemon=True,
            )
            self._thread.start()
            return self.status_unlocked()

    def cancel(self) -> dict[str, Any]:
        with self._lock:
            if self._status.get("state") not in ACTIVE_STATES:
                raise RuntimeError("RAG indexing is not running")
            self._cancel.set()
            self._status.update({
                "state": "stopping",
                "message": "Stopping after the current structure analysis",
                "messageKey": "rag.progress.stopping",
                "messageValues": {},
                "updatedAt": _now_iso(),
            })
            self._persist_unlocked()
            return self.status_unlocked()

    def dismiss_completed(self) -> dict[str, Any]:
        with self._lock:
            if self._status.get("state") != "completed":
                raise RuntimeError("Only a completed RAG indexing status can be dismissed")
            self._status.update({"dismissed": True, "updatedAt": _now_iso()})
            self._persist_unlocked()
            self._status = _idle_status()
            return self.status_unlocked()

    def _persist_unlocked(self) -> None:
        collection_id = self._status.get("collectionId")
        if collection_id:
            self.service.store.save_json(collection_id, "index_job.json", dict(self._status))

    def _on_progress(self, event: dict[str, Any]) -> None:
        with self._lock:
            elapsed = max(0.0, time.monotonic() - self._started)
            analysis_current = int(event.get("analysis_current", self._status.get("analysisCurrent", 0)))
            analysis_total = int(event.get("analysis_total", self._status.get("analysisTotal", 0)))
            eta = None
            if analysis_current > 0 and analysis_total >= analysis_current:
                eta = max(0.0, elapsed / analysis_current * (analysis_total - analysis_current))
            if event.get("stage") in {"save", "done"}:
                eta = 0.0
            self._status.update({
                "stage": event.get("stage", "running"),
                "message": event.get("message", ""),
                "messageKey": event.get("messageKey", ""),
                "messageValues": event.get("messageValues", {}),
                "current": int(event.get("current", 0)),
                "total": int(event.get("total", 0)),
                "percent": float(event.get("percent", 0.0)),
                "elapsedSeconds": elapsed,
                "etaSeconds": eta,
                "analysisCurrent": analysis_current,
                "analysisTotal": analysis_total,
                "reusedCount": int(event.get("reused_count", self._status.get("reusedCount", 0))),
                "failedCount": int(event.get("failed_count", self._status.get("failedCount", 0))),
                "updatedAt": _now_iso(),
            })
            self._persist_unlocked()

    def _run(self, collection_id: str) -> None:
        try:
            analyzer = LocalStructureAnalyzer(self.generation_config)
            stats = self.service.rebuild(
                collection_id,
                force=True,
                progress=self._on_progress,
                analyzer=analyzer,
                should_cancel=self._cancel.is_set,
            )
        except RAGIndexCancelled as exc:
            self._finish("interrupted", str(exc), message_key="rag.progress.interrupted", can_resume=True)
        except Exception as exc:
            self._finish("failed", str(exc), can_resume=True)
        else:
            self._finish("completed", "RAG indexing completed", message_key="rag.progress.completed", stats=stats, can_resume=False)

    def _finish(
        self,
        state: str,
        message: str,
        *,
        message_key: str = "",
        stats: dict[str, Any] | None = None,
        can_resume: bool,
    ) -> None:
        with self._lock:
            elapsed = max(0.0, time.monotonic() - self._started)
            self._status.update({
                "state": state,
                "stage": state,
                "message": message,
                "messageKey": message_key,
                "messageValues": {},
                "elapsedSeconds": elapsed,
                "etaSeconds": 0.0 if state == "completed" else None,
                "percent": 100.0 if state == "completed" else self._status.get("percent", 0.0),
                "canResume": can_resume,
                "stats": stats or {},
                "updatedAt": _now_iso(),
            })
            self._persist_unlocked()
