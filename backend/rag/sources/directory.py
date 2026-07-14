"""Read-only generic directory source adapter."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any, Callable


DEFAULT_EXTENSIONS = (".txt", ".md", ".jsonl")
DEFAULT_EXCLUDES = (".git", ".venv", "__pycache__", "node_modules")


class DirectorySource:
    source_type = "directory"

    def __init__(self, collection: dict[str, Any]):
        self.collection = collection
        self.root = Path(collection["source_path"])
        self.extensions = {str(ext).lower() for ext in collection.get("extensions", DEFAULT_EXTENSIONS)}
        self.excludes = tuple(collection.get("exclude_paths", DEFAULT_EXCLUDES))
        generated = collection.get("rag_store_path")
        self.generated_root = Path(generated).resolve(strict=False) if generated else None

    def is_available(self) -> bool:
        return self.root.exists() and self.root.is_dir()

    def _excluded(self, relative: Path) -> bool:
        parts = set(relative.parts)
        return any(pattern in parts or fnmatch.fnmatch(relative.as_posix(), pattern) for pattern in self.excludes)

    def _inside_generated_data(self, path: Path) -> bool:
        if self.generated_root is None:
            return False
        resolved = path.resolve(strict=False)
        return resolved == self.generated_root or self.generated_root in resolved.parents

    def iter_files(self):
        if not self.is_available():
            return

        for current, dirs, files in os.walk(self.root, followlinks=False):
            current_path = Path(current)
            dirs[:] = [
                name for name in dirs
                if not (current_path / name).is_symlink()
                and not self._inside_generated_data(current_path / name)
                and not self._excluded((current_path / name).relative_to(self.root))
            ]
            for name in sorted(files):
                path = current_path / name
                if path.is_symlink() or self._inside_generated_data(path) or path.suffix.lower() not in self.extensions:
                    continue
                relative = path.relative_to(self.root)
                if self._excluded(relative):
                    continue
                try:
                    stat = path.stat()
                except OSError:
                    continue

                yield path, relative, stat


    def snapshot(self) -> dict[str, Any]:
        if not self.is_available():
            return {"source_missing": True, "files": {}}
        files = {
            relative.as_posix(): {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
            for _, relative, stat in self.iter_files()
        }
        return {"source_missing": False, "files": files}

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
            try:
                raw = path.read_bytes()
            except OSError as exc:
                diagnostics.append(f"Skipped {relative}: {exc}")
                continue
            if b"\x00" in raw[:4096]:
                diagnostics.append(f"Skipped binary file: {relative}")
                continue
            text = raw.decode("utf-8", errors="replace").strip()
            if not text:
                diagnostics.append(f"Skipped empty file: {relative}")
                continue

            documents.append({
                "source_path": relative.as_posix(),
                    "title": path.stem,
                "text": text,
                "mtime_ns": stat.st_mtime_ns,
                "pre_chunked": False,
            })
        return documents, diagnostics
