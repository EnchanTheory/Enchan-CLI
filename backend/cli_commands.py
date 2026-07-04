import os
import sys
import shutil
import urllib.request
import json
import re
from pathlib import Path
from typing import Optional

# Path Resolution
BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent


from ui_theme import interactive_menu, styled_input

from session_log import (
    append_session_event,
    list_session_logs,
    load_session_messages,
    resolve_session_log,
    get_session_metadata,
)


NATURAL_LANGUAGE_ARG_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff01-\uff5e]|[。、「」？]")


def looks_like_natural_language_arg(value: str) -> bool:
    if not value:
        return False
    return bool(NATURAL_LANGUAGE_ARG_RE.search(value))


def load_local_config() -> dict:
    config_path = CLI_DIR / "enchan_config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Warning] Failed to load config: {e}")
    return {}

def save_local_config(config: dict):
    config_path = CLI_DIR / "enchan_config.json"
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[Warning] Failed to save config: {e}")


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

def sync_generation_config_to_active_model(generation_config: dict, active_model_name: str, backend_mode: str):
    """Loads official model recommendations, merges with user-set JSON overrides, and updates generation_config in-place."""
    local_cfg = load_local_config()
    
    # 1. Start with system baseline defaults
    default_params = {
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 40,
        "presence_penalty": 0.0,
        "yarn_factor": 1.0,
        "max_new_tokens": -1,
        "max_input_tokens": 131072,
    }
    
    # 2. Try loading official recommended params from the Ollama Modelfile manifest
    if active_model_name and backend_mode in ("ollama", "enchan"):
        try:
            from enchan_llama_backend import resolve_ollama_model_to_blob
            _, official_params = resolve_ollama_model_to_blob(active_model_name)
            if official_params:
                if "temperature" in official_params:
                    default_params["temperature"] = float(official_params["temperature"])
                if "top_p" in official_params:
                    default_params["top_p"] = float(official_params["top_p"])
                if "top_k" in official_params:
                    default_params["top_k"] = int(official_params["top_k"])
                if "presence_penalty" in official_params:
                    default_params["presence_penalty"] = float(official_params["presence_penalty"])
        except Exception:
            pass
            
    # 3. Apply user-set manual overrides from enchan_config.json IF THEY EXIST
    if "temperature" in local_cfg:
        default_params["temperature"] = float(local_cfg["temperature"])
    if "top_p" in local_cfg:
        default_params["top_p"] = float(local_cfg["top_p"])
    if "top_k" in local_cfg:
        default_params["top_k"] = int(local_cfg["top_k"])
    if "presence_penalty" in local_cfg:
        default_params["presence_penalty"] = float(local_cfg["presence_penalty"])
    if "max_new_tokens" in local_cfg:
        default_params["max_new_tokens"] = int(local_cfg["max_new_tokens"])
    if "ollama_ctx" in local_cfg:
        default_params["max_input_tokens"] = int(local_cfg["ollama_ctx"])
    if "yarn_factor" in local_cfg:
        default_params["yarn_factor"] = float(local_cfg["yarn_factor"])
        
    # 4. Synchronize all values back to the generation_config in-place
    generation_config["temperature"] = default_params["temperature"]
    generation_config["top_p"] = default_params["top_p"]
    generation_config["top_k"] = default_params["top_k"]
    generation_config["presence_penalty"] = default_params["presence_penalty"]
    generation_config["yarn_factor"] = default_params["yarn_factor"]
    generation_config["max_new_tokens"] = default_params["max_new_tokens"]
    generation_config["max_input_tokens"] = default_params["max_input_tokens"]

def print_cli_help():
    """Deprecated fallback helper. Commands are now declarative in registry."""
    from backend.commands.general import handle_help
    handle_help(file_context="")

def print_license():
    """Deprecated fallback helper. Commands are now declarative in registry."""
    from backend.commands.general import handle_license
    handle_license(file_context="")

def handle_cli_command(
    user_input: str,
    chat_history: list[dict],
    file_context: str,
    loaded_files: list[str],
    generation_config: dict,
    model=None,
    session_log_path: Path | None = None,
    agent_mode: bool = False,
    memory_recorder=None,
    tokenizer=None,
) -> tuple[bool, str, bool]:
    """Dynamically dispatches slash commands to declarative core registry handlers."""
    parts = user_input.strip().split()
    if not parts:
        return False, file_context, False
        
    command = parts[0].lower()
    
    # Lazy Import the commands packages so everything is self-registered inside registry
    from backend.commands import registry
    
    if command in registry.commands:
        context = {
            "user_input": user_input,
            "chat_history": chat_history,
            "file_context": file_context,
            "loaded_files": loaded_files,
            "generation_config": generation_config,
            "model": model,
            "session_log_path": session_log_path,
            "agent_mode": agent_mode,
            "memory_recorder": memory_recorder,
            "tokenizer": tokenizer,
        }
        return registry.commands[command].handler(**context)
        
    print(f"[Error] Unknown command: {command}. Type /help for available commands.")
    return True, file_context, False
