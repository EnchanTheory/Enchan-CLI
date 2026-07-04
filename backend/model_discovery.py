import json
import urllib.request
from pathlib import Path

def _is_gguf_file(path: str | Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"GGUF"
    except Exception:
        return False


def filter_enchan_gguf_models(models: list[str]) -> list[str]:
    """Keep only installed Ollama tags that resolve to a GGUF model blob."""
    try:
        from enchan_llama_backend import resolve_ollama_model_to_blob
    except Exception:
        return []

    gguf_models = []
    for model_name in models:
        try:
            resolved_path, _ = resolve_ollama_model_to_blob(model_name)
        except Exception:
            resolved_path = None
        if resolved_path and _is_gguf_file(resolved_path):
            gguf_models.append(model_name)
    return gguf_models


def list_installed_ollama_models(host: str) -> list[str]:
    """Return installed Ollama model tags via the API, falling back to local manifests."""
    try:
        url = host.rstrip("/") + "/api/tags"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        models = []
        manifest_root = Path.home() / ".ollama" / "models" / "manifests" / "registry.ollama.ai" / "library"
        if manifest_root.exists():
            for model_dir in manifest_root.iterdir():
                if model_dir.is_dir():
                    for tag_file in model_dir.iterdir():
                        if tag_file.is_file():
                            models.append(f"{model_dir.name}:{tag_file.name}")
        return models
