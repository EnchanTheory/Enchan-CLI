import json
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
        from backend.enchan_llama_backend import resolve_ollama_model_to_blob
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
