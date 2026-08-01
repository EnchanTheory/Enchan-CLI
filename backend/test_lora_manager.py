import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import backend.enchan_llama_backend as llama_backend
import backend.lora_manager as lora_manager


def _manager(model: str = "model:test") -> lora_manager.MascotLoraManager:
    return lora_manager.MascotLoraManager(
        backend_mode="enchan",
        args=SimpleNamespace(gguf_model="", ollama_model=model),
        generation_config={},
        active_mascot=lambda: "tikta",
    )


def _write_manifest(root: Path, adapter: Path, *, model: str = "model:test") -> None:
    mascot_dir = root / "tikta"
    mascot_dir.mkdir(parents=True, exist_ok=True)
    (mascot_dir / "manifest.json").write_text(json.dumps({
        "adapterPath": str(adapter),
        "modelRef": model,
        "sourcePath": str(root / "training"),
        "createdAt": "2026-08-01T00:00:00+00:00",
    }), encoding="utf-8")


class MascotLoraStatusTests(unittest.TestCase):
    def test_detach_disables_attachment_without_deleting_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter = root / "tikta" / "adapter.gguf"
            adapter.parent.mkdir(parents=True)
            adapter.write_bytes(b"GGUF")
            _write_manifest(root, adapter)
            with patch.object(lora_manager, "LORA_DATA_DIR", root), patch.object(
                llama_backend, "is_enchan_lora_adapter_loaded", return_value=True
            ), patch.object(llama_backend, "shutdown_enchan_llama") as shutdown:
                manager = _manager()
                status = manager.detach("tikta")

            self.assertEqual(status["state"], "detached")
            self.assertFalse(status["enabled"])
            self.assertTrue(adapter.is_file())
            self.assertIsNone(manager.active_adapter("tikta", "model:test"))
            shutdown.assert_called_once_with()

    def test_active_adapter_is_scoped_by_mascot_and_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter = root / "tikta" / "adapter.gguf"
            adapter.parent.mkdir(parents=True)
            adapter.write_bytes(b"GGUF")
            _write_manifest(root, adapter)
            with patch.object(lora_manager, "LORA_DATA_DIR", root):
                manager = _manager()
                self.assertEqual(manager.active_adapter("tikta", "model:test"), adapter.resolve())
                self.assertIsNone(manager.active_adapter("other", "model:test"))
                self.assertIsNone(manager.active_adapter("tikta", "model:other"))
    def test_restores_source_and_distinguishes_generated_from_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter = root / "tikta" / "adapter.gguf"
            adapter.parent.mkdir(parents=True)
            adapter.write_bytes(b"GGUF")
            _write_manifest(root, adapter)
            with patch.object(lora_manager, "LORA_DATA_DIR", root), patch.object(
                llama_backend, "is_enchan_lora_adapter_loaded", return_value=False
            ):
                status = _manager().status("tikta")

            self.assertEqual(status["state"], "ready")
            self.assertEqual(status["sourcePath"], str(root / "training"))
            self.assertTrue(status["adapterExists"])
            self.assertFalse(status["runtimeLoaded"])

    def test_reports_loaded_and_missing_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter = root / "tikta" / "adapter.gguf"
            adapter.parent.mkdir(parents=True)
            adapter.write_bytes(b"GGUF")
            _write_manifest(root, adapter)
            with patch.object(lora_manager, "LORA_DATA_DIR", root), patch.object(
                llama_backend, "is_enchan_lora_adapter_loaded", return_value=True
            ):
                self.assertEqual(_manager().status("tikta")["state"], "attached")
                adapter.unlink()
                status = _manager().status("tikta")

            self.assertEqual(status["state"], "missing")
            self.assertFalse(status["adapterExists"])


if __name__ == "__main__":
    unittest.main()