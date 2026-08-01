"""Local GGUF-native LoRA training and mascot attachment management."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent
LORA_DATA_DIR = CLI_DIR / "data" / "lora" / "mascots"
LORA_WORK_DIR = CLI_DIR / "temp_workspace" / "lora"
TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
EXCLUDED_DIRS = {".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv"}
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_DATASET_BYTES = 32 * 1024 * 1024
MIN_DATASET_CHARS = 2048
MODEL_BLOB_PATTERN = re.compile(r"^sha256-([0-9a-f]{64})$")


def _runtime_platform_dir() -> str:
    if sys.platform == "win32":
        return "win-x64"
    if sys.platform == "darwin":
        import platform
        return f"macos-{'arm64' if platform.machine() == 'arm64' else 'x64'}"
    return "linux-x64"


def _trainer_path() -> Path:
    name = "enchan-lora-train.exe" if sys.platform == "win32" else "enchan-lora-train"
    return BACKEND_DIR / "bin" / _runtime_platform_dir() / "lora" / name


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decode_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Text file is not UTF-8 or Windows Japanese text: {path.name}")


def _model_identity(path: Path) -> str:
    match = MODEL_BLOB_PATTERN.fullmatch(path.name)
    if match:
        return f"sha256:{match.group(1)}"
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        while chunk := model_file.read(8 * 1024 * 1024):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


class MascotLoraManager:
    def __init__(
        self,
        *,
        backend_mode: str,
        args: Any,
        generation_config: dict[str, Any],
        active_mascot: Callable[[], str],
    ) -> None:
        self.backend_mode = backend_mode
        self.args = args
        self.generation_config = generation_config
        self.active_mascot = active_mascot
        self._lock = threading.RLock()
        self._process: subprocess.Popen[str] | None = None
        self._cancel = threading.Event()
        self._job = self._idle_job()

    @staticmethod
    def _idle_job() -> dict[str, Any]:
        return {
            "state": "idle",
            "phase": "idle",
            "percent": 0,
            "message": "",
            "messageKey": "",
            "messageValues": {},
            "mascotId": "",
            "sourcePath": "",
            "startedAt": None,
            "finishedAt": None,
            "error": "",
        }

    @staticmethod
    def _manifest_path(mascot_id: str) -> Path:
        return LORA_DATA_DIR / mascot_id / "manifest.json"

    def _load_manifest(self, mascot_id: str) -> dict[str, Any] | None:
        path = self._manifest_path(mascot_id)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def is_busy(self) -> bool:
        with self._lock:
            return self._job["state"] in {"preparing", "running", "cancelling"}

    def status(self, mascot_id: str | None = None) -> dict[str, Any]:
        selected = mascot_id or self.active_mascot()
        with self._lock:
            job = dict(self._job)
        manifest = self._load_manifest(selected)
        current_model = str(
            getattr(self.args, "gguf_model", "") or getattr(self.args, "ollama_model", "")
        ).strip()
        model_match = bool(manifest and manifest.get("modelRef") == current_model)
        adapter_path = Path(str(manifest.get("adapterPath", ""))) if manifest else None
        adapter_exists = bool(adapter_path and adapter_path.is_file())
        runtime_loaded = False
        if adapter_exists and model_match:
            from backend.enchan_llama_backend import is_enchan_lora_adapter_loaded
            runtime_loaded = is_enchan_lora_adapter_loaded(adapter_path)
        if manifest and not job.get("sourcePath"):
            job["sourcePath"] = str(manifest.get("sourcePath", ""))
        if manifest and job["state"] in {"idle", "completed"}:
            if not adapter_exists:
                state = "missing"
                message = f"Adapter file is missing: {adapter_path}"
                message_key = "lora.status.missing"
                message_values = {}
            elif not model_match:
                state = "saved"
                message = f"Training is saved for {manifest.get('modelRef', 'another model')}"
                message_key = "lora.status.savedFor"
                message_values = {"model": str(manifest.get("modelRef", "another model"))}
            elif runtime_loaded:
                state = "attached"
                message = f"Loaded by the running {current_model} engine"
                message_key = "lora.status.attached"
                message_values = {"model": current_model}
            else:
                state = "ready"
                message = f"Generated for {current_model}; it will load on the next chat"
                message_key = "lora.status.readyFor"
                message_values = {"model": current_model}
            job.update({
                "state": state,
                "percent": 100,
                "message": message,
                "messageKey": message_key,
                "messageValues": message_values,
            })
        return {
            **job,
            "available": _trainer_path().is_file(),
            "backendSupported": self.backend_mode == "enchan",
            "modelMatch": model_match,
            "adapterExists": adapter_exists,
            "runtimeLoaded": runtime_loaded,
            "mascotId": selected,
            "adapter": manifest,
        }

    def active_adapter(self, mascot_id: str, model_ref: str) -> Path | None:
        manifest = self._load_manifest(mascot_id)
        if not manifest or manifest.get("modelRef") != model_ref:
            return None
        adapter = Path(str(manifest.get("adapterPath", "")))
        return adapter.resolve() if adapter.is_file() else None

    def start(self, mascot_id: str, source_path: str) -> dict[str, Any]:
        if self.backend_mode != "enchan":
            raise RuntimeError("Mascot training requires the Enchan backend")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", mascot_id):
            raise ValueError("Invalid mascot ID")
        source = Path(source_path).expanduser().resolve()
        if not source.is_dir():
            raise FileNotFoundError(f"Training directory does not exist: {source}")
        if not _trainer_path().is_file():
            raise FileNotFoundError(f"Enchan-LoRA trainer is not installed: {_trainer_path()}")
        with self._lock:
            if self.is_busy():
                raise RuntimeError("Another mascot training job is already running")
            self._cancel.clear()
            self._job = {
                **self._idle_job(),
                "state": "preparing",
                "phase": "scanning",
                "percent": 2,
                "message": "Reading local training text",
                "messageKey": "lora.progress.reading",
                "mascotId": mascot_id,
                "sourcePath": str(source),
                "startedAt": _utc_now(),
            }
        threading.Thread(
            target=self._run,
            args=(mascot_id, source),
            name=f"enchan-lora-{mascot_id}",
            daemon=True,
        ).start()
        return self.status(mascot_id)

    def cancel(self) -> dict[str, Any]:
        with self._lock:
            if not self.is_busy():
                return dict(self._job)
            self._cancel.set()
            self._job["state"] = "cancelling"
            self._job["message"] = "Stopping training"
            self._job["messageKey"] = "lora.progress.stopping"
            process = self._process
        if process is not None and process.poll() is None:
            process.terminate()
        return dict(self._job)

    def _set_job(self, **values: Any) -> None:
        with self._lock:
            self._job.update(values)

    def _collect_dataset(self, source: Path, destination: Path) -> list[str]:
        files = []
        total_bytes = 0
        for path in sorted(source.rglob("*"), key=lambda item: str(item).casefold()):
            if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            if any(part in EXCLUDED_DIRS or part.startswith(".") for part in path.relative_to(source).parts[:-1]):
                continue
            size = path.stat().st_size
            if size > MAX_FILE_BYTES:
                continue
            total_bytes += size
            if total_bytes > MAX_DATASET_BYTES:
                raise ValueError("Training text exceeds the 32 MB local limit")
            files.append(path)
        if not files:
            raise ValueError("No .txt, .md, or .markdown training files were found")

        sections = []
        relative_names = []
        for path in files:
            text = _decode_text(path).strip()
            if not text:
                continue
            relative = path.relative_to(source).as_posix()
            relative_names.append(relative)
            sections.append(f"\n\n### {relative}\n\n{text}")
        if not sections:
            raise ValueError("Training files are empty")
        dataset = "".join(sections).strip()
        seed = dataset
        while len(dataset) < MIN_DATASET_CHARS:
            dataset += "\n\n---\n\n" + seed
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(dataset, encoding="utf-8", newline="\n")
        return relative_names

    def _resolve_model(self) -> tuple[str, Path]:
        model_ref = str(getattr(self.args, "gguf_model", "") or getattr(self.args, "ollama_model", "")).strip()
        if not model_ref:
            raise ValueError("No Enchan model is selected")
        from backend.enchan_llama_backend import resolve_ollama_model_to_blob
        resolved, _ = resolve_ollama_model_to_blob(model_ref)
        if not resolved:
            raise FileNotFoundError(f"Could not resolve selected model: {model_ref}")
        return model_ref, Path(resolved).resolve()

    def _list_target(self, model_path: Path) -> str:
        result = subprocess.run(
            [
                str(_trainer_path()),
                "--model", str(model_path),
                "--list-targets",
                "--target", "blk.*.attn_output.weight",
            ],
            cwd=str(_trainer_path().parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Could not inspect LoRA targets")
        targets = [
            line.split("\t", 1)[0].strip()
            for line in result.stdout.splitlines()
            if line.strip().startswith("blk.") and "\t" in line
        ]
        if not targets:
            raise RuntimeError("The selected model has no supported attention output target")
        return max(targets, key=lambda name: int(name.split(".", 2)[1]))

    def _run_process(self, command: list[str], *, phase: str, percent: int) -> subprocess.CompletedProcess[str]:
        self._set_job(state="running", phase=phase, percent=percent)
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        with self._lock:
            self._process = subprocess.Popen(
                command,
                cwd=str(_trainer_path().parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )
            process = self._process
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        def read_stderr() -> None:
            assert process.stderr is not None
            for line in process.stderr:
                stderr_lines.append(line)
                message = line.strip()
                if message.startswith("[Enchan-LoRA]"):
                    self._set_job(message=message.removeprefix("[Enchan-LoRA]").strip(), messageKey="")

        reader = threading.Thread(target=read_stderr, daemon=True)
        reader.start()
        assert process.stdout is not None
        stdout_lines.extend(process.stdout.readlines())
        returncode = process.wait()
        reader.join(timeout=2)
        with self._lock:
            self._process = None
        if self._cancel.is_set():
            raise InterruptedError("Training was cancelled")
        return subprocess.CompletedProcess(command, returncode, "".join(stdout_lines), "".join(stderr_lines))

    def _run(self, mascot_id: str, source: Path) -> None:
        work_dir = LORA_WORK_DIR / mascot_id
        adapter_dir = LORA_DATA_DIR / mascot_id
        dataset_path = work_dir / "dataset.txt"
        adapter_path = adapter_dir / "adapter.gguf"
        try:
            files = self._collect_dataset(source, dataset_path)
            self._set_job(phase="model", percent=8, message="Resolving the selected GGUF model", messageKey="lora.progress.resolvingModel")
            model_ref, model_path = self._resolve_model()
            target = self._list_target(model_path)
            if self._cancel.is_set():
                raise InterruptedError("Training was cancelled")

            from backend.enchan_llama_backend import shutdown_enchan_llama
            shutdown_enchan_llama()
            adapter_dir.mkdir(parents=True, exist_ok=True)
            command = [
                str(_trainer_path()),
                "--model", str(model_path),
                "--data", str(dataset_path),
                "--out", str(adapter_path),
                "--work-dir", str(work_dir / "native"),
                "--target", target,
                "--rank", "2",
                "--alpha", "4",
                "--ctx", "256",
                "--batch", "256",
                "--ubatch", "32",
                "--epochs", "1",
                "--lr", "1e-4",
                "--gpu-layers", "0",
            ]
            result = self._run_process(command, phase="training", percent=20)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "Training failed")

            self._set_job(phase="validating", percent=90, message="Validating the new adapter", messageKey="lora.progress.validating")
            validation = subprocess.run(
                [str(_trainer_path()), "--model", str(model_path), "--validate-adapter", str(adapter_path)],
                cwd=str(_trainer_path().parent),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
                check=False,
            )
            if validation.returncode != 0:
                raise RuntimeError(validation.stderr.strip() or "Adapter validation failed")
            manifest = {
                "schemaVersion": 1,
                "mascotId": mascot_id,
                "state": "ready",
                "adapterPath": str(adapter_path.resolve()),
                "modelRef": model_ref,
                "modelPath": str(model_path),
                "modelIdentity": _model_identity(model_path),
                "modelSize": model_path.stat().st_size,
                "target": target,
                "rank": 2,
                "alpha": 4,
                "sourcePath": str(source),
                "sourceFiles": files,
                "createdAt": _utc_now(),
            }
            manifest_path = self._manifest_path(mascot_id)
            temp = manifest_path.with_suffix(".tmp")
            temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(manifest_path)
            self._set_job(
                state="completed",
                phase="done",
                percent=100,
                message="Training complete. The adapter will attach on the next chat.",
                messageKey="lora.progress.complete",
                finishedAt=_utc_now(),
                error="",
            )
        except InterruptedError as exc:
            self._set_job(
                state="cancelled", phase="cancelled", message=str(exc),
                messageKey="lora.progress.cancelled",
                finishedAt=_utc_now(), error="",
            )
        except Exception as exc:
            self._set_job(
                state="failed", phase="failed", message="Training failed",
                messageKey="lora.progress.failed",
                finishedAt=_utc_now(), error=str(exc),
            )
