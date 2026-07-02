import os
import sys
import logging

# Suppress Hugging Face, Transformers, and Hub console warnings to keep CLI output pristine
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

import gc
import time
import re
import uuid
import shutil
import argparse
import subprocess
import threading
import json
import urllib.request
import urllib.error
from pathlib import Path
try:
    import msvcrt
except ImportError:
    msvcrt = None

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# --- Path Resolution for Imports ---
BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent


from session_log import (
    append_session_event,
    list_session_logs,
    load_session_messages,
    new_session_log_path,
    resolve_session_log,
    get_session_metadata,
)

MODEL_ID = "google/gemma-4-e2b-it"

def estimate_text_tokens_rough(text: str) -> int:
    if not text:
        return 0
    cjk_count = sum(
        1
        for ch in text
        if "\u3040" <= ch <= "\u30ff"
        or "\u3400" <= ch <= "\u4dbf"
        or "\u4e00" <= ch <= "\u9fff"
        or "\uf900" <= ch <= "\ufaff"
    )
    if cjk_count:
        return max(1, cjk_count + ((len(text) - cjk_count) // 4))
    return max(1, len(text) // 4)

def sanitize_for_json(text: str) -> str:
    return text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")

def format_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)

def format_size(num_bytes: float) -> str:
    """Human-readable byte size, e.g. 4.3 GB."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"

def strip_thought_blocks(text: str) -> str:
    """Removes <thought>...</thought> and <think>...</think> blocks to keep multi-turn context clean."""
    if not text:
        return text
    text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()

class RunningModelTokenizer:
    """現在ロードされて動作中のモデル（Ollamaまたはllama-server）のAPIを直接使ってトークン化を行う軽量クラス"""
    def __init__(self, backend_type: str = "", host: str = "", model_name: str = ""):
        self._backend_type = backend_type
        self._host = host
        self._model_name = model_name

    def _get_active_config(self) -> tuple[str, str, str]:
        # Dynamically fetch config to support hot-swapping models/backends in the same session!
        from cli_commands import load_local_config
        local_cfg = load_local_config()
        backend_mode = local_cfg.get("backend", self._backend_type or "enchan")
        
        if backend_mode == "enchan":
            host = "http://localhost:8080"
            model = local_cfg.get("gguf_model", self._model_name)
        else:
            host = local_cfg.get("ollama_host", self._host or "http://localhost:11434")
            model = local_cfg.get("ollama_model", self._model_name)
            
        return backend_mode, host, model

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        if not text:
            return []
        import urllib.request
        import json
        
        backend_mode, host, model = self._get_active_config()
        
        if backend_mode == "enchan":
            url = f"{host}/tokenize"
            payload = {"content": text}
        else:
            url = f"{host}/api/tokenize"
            payload = {"model": model, "prompt": text}
            
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("tokens", [])
        except Exception:
            # Simple fallback estimation
            from enchan_chat import estimate_text_tokens_rough
            return [0] * estimate_text_tokens_rough(text)

    def decode(self, token_ids: list[int], skip_special_tokens: bool = True) -> str:
        if not token_ids:
            return ""
        import urllib.request
        import json
        
        backend_mode, host, model = self._get_active_config()
        
        if backend_mode == "enchan":
            url = f"{host}/detokenize"
            payload = {"tokens": token_ids}
        else:
            url = f"{host}/api/detokenize"
            payload = {"model": model, "tokens": token_ids}
            
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("content", "") or data.get("prompt", "")
        except Exception:
            return f"[Detokenize Fallback: {len(token_ids)} tokens]"

    def apply_chat_template(self, messages: list[dict], add_generation_prompt: bool = True, tokenize: bool = False) -> str:
        _, _, model = self._get_active_config()
        name = str(model).lower()
        is_qwen = "qwen" in name
        is_llama = "llama" in name or "enchan" in name
        is_gemma = "gemma" in name or (not is_qwen and not is_llama)
        
        formatted = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "model":
                role = "assistant"
                
            if is_gemma:
                formatted += f"<start_of_turn>{role}\n{content}<end_of_turn>\n"
            elif is_qwen:
                formatted += f"<|im_start|>{role}\n{content}<|im_end|>\n"
            elif is_llama:
                formatted += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
                
        if add_generation_prompt:
            if is_gemma:
                formatted += "<start_of_turn>model\n"
            elif is_qwen:
                formatted += "<|im_start|>assistant\n"
            elif is_llama:
                formatted += "<|start_header_id|>assistant<|end_header_id|>\n\n"
                
        return formatted

def load_enchan_tokenizer_for_ollama(model_name: str = ""):
    return RunningModelTokenizer()

from reading_agent import execute_reading_pipeline
from context_compression import (
    COSMIC_AVAILABLE,
    compress_context,
    compress_chat_history,
    count_text_tokens,
    format_count,
    print_source_metrics,
)
from agent_tools import (
    AGENT_MAX_ITERATIONS,
    AGENT_SYSTEM_PROMPT,
    NORMAL_MODE_TOOL_GUIDANCE,
    ToolCallStoppingCriteria,
    execute_agent_tool,
    parse_agent_tool_call,
    truncate_observation,
)
from ollama_backend import (
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_MODEL,
    ensure_ollama_running,
    generate_ollama_response,
    run_ollama_once,
    run_ollama_agent_turn,
)
from memory_store import (
    build_memory_prompt_section,
    ensure_memory_dirs,
    load_memory_context,
)
from source_loader import extract_path_and_query, read_directory_recursive
from ui_theme import interactive_menu, make_prompt_style, print_python_execution, print_python_timeout, print_response_header

from cli_commands import (
    load_local_config,
    save_local_config,
    sync_generation_config_to_active_model,
    handle_cli_command,
)

if not COSMIC_AVAILABLE:
    print("[Warning] Could not load Enchan Engine DLL. External context compression will be disabled.")

# --- Hugging Face Backend (Dynamically Loaded) ---

def build_agent_goal_prompt(goal: str, memory_context: str = "") -> str:
    memory_section = build_memory_prompt_section(memory_context)
    return f"{AGENT_SYSTEM_PROMPT}{memory_section}\n\nGoal:\n{goal}"


PYTHON_EXECUTION_HINT_RE = re.compile(
    r"(実行|走らせ|動かし|叩い|試し|run|execute|launch)",
    re.IGNORECASE,
)


def wants_python_file_execution(query: str) -> bool:
    return bool(query and PYTHON_EXECUTION_HINT_RE.search(query))


def run_python_file_from_prompt(
    script_path: Path,
    query: str,
    session_log_path: Path,
    timeout_sec: int = 120,
) -> None:
    root = CLI_DIR.resolve()
    resolved_script = script_path.resolve()
    if resolved_script != root and root not in resolved_script.parents:
        print(f"[Error] Refusing to execute Python outside CLI root: {resolved_script}")
        append_session_event(
            session_log_path,
            {
                "type": "python_file_execution_refused",
                "path": str(resolved_script),
                "reason": "outside_cli_root",
            },
        )
        return

    cmd = [sys.executable, str(resolved_script)]
    append_session_event(
        session_log_path,
        {
            "type": "python_file_execution_started",
            "path": str(resolved_script),
            "query": query,
            "cmd": cmd,
            "timeout_sec": timeout_sec,
        },
    )
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(resolved_script.parent),
            capture_output=True,
            timeout=timeout_sec,
        )

        def decode_smart(b: bytes) -> str:
            if not b:
                return ""
            try:
                return b.decode("utf-8")
            except UnicodeDecodeError:
                return b.decode("cp932", errors="replace")

        stdout = decode_smart(completed.stdout)
        stderr = decode_smart(completed.stderr)
        
        print(f"\x1b[38;2;190;170;120m╭── [ Python Execution ] ──\x1b[0m")
        print(f"\x1b[38;2;190;170;120m│\x1b[0m \x1b[38;2;210;200;200mexit_code={completed.returncode}\x1b[0m")
        if stdout:
            print(f"\x1b[38;2;190;170;120m│\x1b[0m \x1b[38;2;120;160;120m[stdout]\x1b[0m")
            for line in truncate_observation(stdout, max_chars=12000).splitlines():
                print(f"\x1b[38;2;190;170;120m│\x1b[0m \x1b[38;2;210;200;200m{line}\x1b[0m")
        if stderr:
            print(f"\x1b[38;2;190;170;120m│\x1b[0m \x1b[38;2;180;100;100m[stderr]\x1b[0m")
            for line in truncate_observation(stderr, max_chars=12000).splitlines():
                print(f"\x1b[38;2;190;170;120m│\x1b[0m \x1b[38;2;180;100;100m{line}\x1b[0m")
        print(f"\x1b[38;2;190;170;120m╰{'─'*30}\x1b[0m")
        append_session_event(
            session_log_path,
            {
                "type": "python_file_execution_finished",
                "path": str(resolved_script),
                "returncode": completed.returncode,
                "stdout": truncate_observation(stdout, max_chars=12000),
                "stderr": truncate_observation(stderr, max_chars=12000),
            },
        )
    except subprocess.TimeoutExpired as e:
        def decode_smart(b) -> str:
            if isinstance(b, str): return b
            if not b: return ""
            try: return b.decode("utf-8")
            except UnicodeDecodeError: return b.decode("cp932", errors="replace")
            
        stdout = decode_smart(e.stdout)
        stderr = decode_smart(e.stderr)
        
        print(f"[Host] Observation: Python execution timed out after {timeout_sec}s.")
        if stdout:
            print("[stdout]")
            print(truncate_observation(stdout, max_chars=12000))
        if stderr:
            print("[stderr]")
            print(truncate_observation(stderr, max_chars=12000))
        append_session_event(
            session_log_path,
            {
                "type": "python_file_execution_timeout",
                "path": str(resolved_script),
                "timeout_sec": timeout_sec,
                "stdout": truncate_observation(stdout, max_chars=12000),
                "stderr": truncate_observation(stderr, max_chars=12000),
            },
        )
    except Exception as e:
        print(f"[Error] Python execution failed: {e}")
        append_session_event(
            session_log_path,
            {
                "type": "python_file_execution_error",
                "path": str(resolved_script),
                "message": str(e),
            },
        )


def select_startup_backend(default_backend: str) -> str:
    ollama_ready = shutil.which("ollama") is not None

    choices = [
        ("enchan", "Local: Enchan Llama", True),
        ("ollama", "Local: Ollama API chat", ollama_ready),
    ]

    valid_choices = {name for name, _, ready in choices if ready}
    default_backend = default_backend if default_backend in valid_choices else "enchan"
    
    current_idx = 0
    for i, (name, _, _) in enumerate(choices):
        if name == default_backend:
            current_idx = i
            break

    # Alias check for text input fallback
    is_interactive = sys.stdin.isatty() and (msvcrt is not None or (sys.platform != "win32"))
    if not is_interactive:
        # Re-implementing text fallback alias check just for backend since interactive_menu is generic
        # but interactive_menu already handles basic digits. We'll let interactive_menu do it.
        pass

    selected_idx = interactive_menu("Backend Selection", choices, default_idx=current_idx)
    if selected_idx >= 0:
        return choices[selected_idx][0]
    return default_backend

def response_model_label(generation_config: dict) -> str:
    model_id = str(generation_config.get("model_id") or generation_config.get("ollama_model") or "model")
    if model_id.startswith("ollama:"):
        model_id = model_id[len("ollama:"):]
    elif model_id.startswith("enchan:"):
        model_id = model_id[len("enchan:"):]
    if model_id.endswith(".gguf") or "\\" in model_id or "/" in model_id:
        model_id = Path(model_id).stem
    return model_id or "model"


def response_backend_label(generation_config: dict) -> str:
    backend = str(generation_config.get("backend") or "enchan").lower()
    model_id = str(generation_config.get("model_id") or "")
    if ":" in model_id:
        prefix = model_id.split(":", 1)[0].lower()
        if prefix in {"ollama", "enchan", "hf"}:
            backend = prefix
    return backend or "enchan"


def response_label(generation_config: dict) -> str:
    return f"{response_backend_label(generation_config)}:{response_model_label(generation_config)}"


def print_agent_turn_header(generation_config: dict) -> None:
    print_response_header(response_label(generation_config))

def standalone_ollama_pull(model_name: str) -> bool:
    """
    Downloads an Ollama model directly from the registry without needing the Ollama daemon.
    Saves blobs and manifests exactly where Ollama expects them (~/.ollama/models/).
    """
    print(f"\n[System] Standalone registry pull initiated for: {model_name}")
    
    # Parse model name (e.g. gemma:2b or library/gemma:2b)
    if ":" not in model_name:
        model_name += ":latest"
    repo, tag = model_name.split(":", 1)
    if "/" not in repo:
        repo = f"library/{repo}"

    registry_base = "https://registry.ollama.ai/v2"
    manifest_url = f"{registry_base}/{repo}/manifests/{tag}"

    ollama_dir = Path.home() / ".ollama" / "models"
    blobs_dir = ollama_dir / "blobs"
    manifest_dir = ollama_dir / "manifests" / "registry.ollama.ai" / repo
    
    blobs_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    print(f"[System] Fetching manifest from registry.ollama.ai...")
    req = urllib.request.Request(manifest_url, headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            manifest_bytes = resp.read()
            manifest = json.loads(manifest_bytes)
    except urllib.error.HTTPError as e:
        print(f"[Error] Failed to fetch manifest ({e.code}). Model might not exist.")
        return False
    except Exception as e:
        print(f"[Error] Network error while fetching manifest: {e}")
        return False

    layers = manifest.get("layers", [])
    if "config" in manifest:
        layers.append(manifest["config"])

    total_size = sum(layer.get("size", 0) for layer in layers)
    downloaded_size = 0

    print(f"[System] Downloading {len(layers)} layers (Total: {format_size(total_size)})...")

    for layer in layers:
        digest = layer.get("digest")
        if not digest:
            continue
        
        blob_path = blobs_dir / digest.replace(":", "-")
        layer_size = layer.get("size", 0)

        if blob_path.exists() and blob_path.stat().st_size == layer_size:
            downloaded_size += layer_size
            continue

        blob_url = f"{registry_base}/{repo}/blobs/{digest}"
        
        # We need a custom opener to handle redirects (often S3 buckets) and stream the download
        try:
            req = urllib.request.Request(blob_url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                with open(blob_path, "wb") as f:
                    while True:
                        chunk = resp.read(8192 * 4)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Progress bar
                        if total_size > 0:
                            percent = int(downloaded_size * 100 / total_size)
                            percent = min(100, percent)
                            bar_length = 30
                            filled_length = int(bar_length * percent // 100)
                            bar = '█' * filled_length + '░' * (bar_length - filled_length)
                            sys.stdout.write(f"\r[Downloading] {bar} {percent}% ({format_size(downloaded_size)} / {format_size(total_size)}) ")
                            sys.stdout.flush()
        except Exception as e:
            print(f"\n[Error] Failed to download blob {digest[:15]}: {e}")
            if blob_path.exists():
                blob_path.unlink() # Clean up partial
            return False

    # Finally, write the manifest
    manifest_file = manifest_dir / tag
    with open(manifest_file, "wb") as f:
        f.write(manifest_bytes)

    print("\n[System] Download complete! Model integrated into Ollama storage.\n")
    return True

ENCHAN_DEFAULT_DOWNLOAD_MODEL = "gemma4:e2b-it-qat"
ENCHAN_DEFAULT_DOWNLOAD_SIZE = "~4.3 GB"


def list_installed_ollama_models(host: str) -> list:
    """Return installed Ollama model tags via the API, falling back to local manifests."""
    try:
        url = host.rstrip("/") + "/api/tags"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        models = []
        try:
            manifest_root = Path.home() / ".ollama" / "models" / "manifests" / "registry.ollama.ai" / "library"
            if manifest_root.exists():
                for model_dir in manifest_root.iterdir():
                    if model_dir.is_dir():
                        for tag_file in model_dir.iterdir():
                            if tag_file.is_file():
                                models.append(f"{model_dir.name}:{tag_file.name}")
        except Exception:
            pass
        return models


def select_startup_model(host: str, title: str = "Select Model") -> Optional[str]:
    """Let the user pick an installed model or download the default one.

    Returns the chosen model tag (which may still need downloading), or None if cancelled.
    When no models are installed, the only option is to download the default model.
    """
    installed = list_installed_ollama_models(host)
    options = [(name, "installed", True) for name in installed]
    offer_download = ENCHAN_DEFAULT_DOWNLOAD_MODEL not in installed
    if offer_download:
        options.append(
            (
                f"Download {ENCHAN_DEFAULT_DOWNLOAD_MODEL} ({ENCHAN_DEFAULT_DOWNLOAD_SIZE})",
                "from registry.ollama.ai",
                True,
            )
        )
    selected_idx = interactive_menu(title, options, default_idx=0)
    if selected_idx < 0:
        return None
    if offer_download and selected_idx == len(options) - 1:
        return ENCHAN_DEFAULT_DOWNLOAD_MODEL
    return installed[selected_idx]

def main():
    local_cfg = load_local_config()

    parser = argparse.ArgumentParser(description="Interactive Enchan CLI")
    default_backend = local_cfg.get("backend", "enchan")
    if default_backend not in {"ollama", "enchan"}:
        default_backend = "enchan"
    parser.add_argument("--backend", choices=["ollama", "enchan"], default=default_backend, help="runtime backend: ollama uses local Ollama; enchan uses Enchan Llama")
    parser.add_argument("--gguf-model", default="", help="path to GGUF model for --backend enchan (interactive startup shows a model picker when omitted)")
    parser.add_argument("--screen-strength", type=float, default=local_cfg.get("screen_strength", 0.2), help="screening strength for --backend enchan (default: 0.2)")
    parser.add_argument("--H-c", type=float, default=local_cfg.get("H_c", 1.6), help="scaling depth H_c for --backend enchan (default: 1.6)")
    parser.add_argument("--m", type=float, default=local_cfg.get("m", 1.5), help="sharpness power m for --backend enchan (default: 1.5)")
    parser.add_argument("--no-ram-guard", action="store_true", help="disable Enchan Llama system RAM reserve guard")
    parser.add_argument("--ram-reserve-ratio", type=float, default=local_cfg.get("ram_reserve_ratio", 0.05), help="fraction of physical RAM to keep free for --backend enchan (default: 0.05)")
    parser.add_argument("--ram-reserve-gb", type=float, default=local_cfg.get("ram_reserve_gb", 1.6), help="minimum GiB of physical RAM to keep free for --backend enchan (default: 1.6)")
    parser.add_argument("--ram-pressure-action", choices=["warn", "kill"], default=local_cfg.get("ram_pressure_action", "warn"), help="what to do when Enchan Llama crosses the RAM reserve (default: warn)")
    parser.add_argument("--llama-mmap", choices=["on", "off"], default=local_cfg.get("llama_mmap", "off"), help="memory-map GGUF model files for --backend enchan (default: off)")
    parser.add_argument("--llama-fit", action="store_true", default=local_cfg.get("llama_fit", False), help="enable llama.cpp --fit memory fitting for --backend enchan")
    parser.add_argument("--ollama-model", default=local_cfg.get("ollama_model", DEFAULT_OLLAMA_MODEL), help=f"Ollama model name for --backend ollama (default: {DEFAULT_OLLAMA_MODEL})")
    parser.add_argument("--ollama-host", default=local_cfg.get("ollama_host", DEFAULT_OLLAMA_HOST), help=f"Ollama API host for --backend ollama (default: {DEFAULT_OLLAMA_HOST})")
    parser.add_argument("--ollama-ctx", type=int, default=local_cfg.get("ollama_ctx", 131072), help="Ollama num_ctx for --backend ollama/enchan (default: 131072)")
    parser.add_argument("--no-ollama-start", action="store_true", help="do not auto-start `ollama serve` when --backend ollama cannot reach the API")
    parser.add_argument("--view-think", action="store_true", default=local_cfg.get("view_think", False), help="show model thinking traces")
    parser.add_argument("--max-new-tokens", type=int, default=local_cfg.get("max_new_tokens", -1), help="maximum generated tokens for --backend ollama (-1 for infinite)")
    parser.add_argument("--temperature", type=float, default=local_cfg.get("temperature", 1.0), help="sampling temperature for --backend ollama (default: 1.0)")
    parser.add_argument("--top-p", type=float, default=local_cfg.get("top_p", 0.95), help="top_p for --backend ollama (default: 0.95)")
    parser.add_argument("--top-k", type=int, default=local_cfg.get("top_k", 64), help="top_k for --backend ollama (default: 64)")
    parser.add_argument("--presence-penalty", type=float, default=local_cfg.get("presence_penalty", 0.0), help="presence penalty for --backend ollama/enchan (default: 0.0)")
    parser.add_argument("--no-thinking", action="store_true", help="Disable thinking mode (Qwen3.6)")
    parser.add_argument("--preserve-thinking", action="store_true", help="Preserve thinking history in chat context (Qwen3.6)")
    parser.add_argument("--text-only", action="store_true", help="Text-only mode (skip vision encoder for Qwen3.6)")
    parser.add_argument("--mtp", action="store_true", help="Enable Multi-Token Prediction (Qwen3.6 MTP)")
    parser.add_argument("--yarn-factor", type=float, default=local_cfg.get("yarn_factor", 1.0), help="YaRN scaling factor for ultra-long context (e.g., 4.0 for >256K)")
    parser.add_argument("--ask", help="run one non-interactive prompt and exit; intended for local agent delegation")
    parser.add_argument("--ask-file", help="read one non-interactive prompt from a UTF-8 file and exit")
    parser.add_argument("--plain", action="store_true", help="with --ask/--ask-file, print only the final assistant response")
    parser.add_argument("--agent", action="store_true", help="enable deterministic ReAct tool execution mode")
    args = parser.parse_args()
    backend_explicit = any(arg == "--backend" or arg.startswith("--backend=") for arg in sys.argv[1:])
    if args.ask and args.ask_file:
        parser.error("--ask and --ask-file cannot be used together")
    single_turn_requested = bool(args.ask or args.ask_file)
    if not backend_explicit and not single_turn_requested and sys.stdin.isatty():
        args.backend = select_startup_backend(args.backend)
    # Dynamic defaults based on official Ollama Modelfile parameters
    active_model_name = args.gguf_model if args.backend == "enchan" and args.gguf_model else args.ollama_model
    if active_model_name:
        try:
            # We import here to avoid circular dependencies
            from enchan_llama_backend import resolve_ollama_model_to_blob
            _, official_params = resolve_ollama_model_to_blob(active_model_name)
            if official_params:
                if "temperature" in official_params and "temperature" not in local_cfg:
                    args.temperature = float(official_params["temperature"])
                if "top_p" in official_params and "top_p" not in local_cfg:
                    args.top_p = float(official_params["top_p"])
                if "top_k" in official_params and "top_k" not in local_cfg:
                    args.top_k = int(official_params["top_k"])
                if "presence_penalty" in official_params and "presence_penalty" not in local_cfg:
                    args.presence_penalty = float(official_params["presence_penalty"])
        except Exception:
            pass
            
    plain_output = bool(args.plain and single_turn_requested)
    backend_mode = "ollama" if single_turn_requested and args.backend == "hf" else args.backend


    session_id = uuid.uuid4().hex
    session_log_path = new_session_log_path()


    agent_mode = bool(args.agent)

    if not plain_output:
        print("=" * 70)
        header_line = f"  Enchan CLI [Backend] {backend_mode}"
        if agent_mode:
            header_line += " [Agent]"
        print(header_line)
        print("=" * 70)
    
    if backend_mode == "enchan":
        import atexit
        from enchan_llama_backend import shutdown_enchan_llama
        atexit.register(shutdown_enchan_llama)

        # Register signal handlers for clean shutdown on termination signals
        import signal
        def handle_termination_signal(signum, frame):
            shutdown_enchan_llama()
            sys.exit(0)
        for sig in (signal.SIGTERM, getattr(signal, 'SIGBREAK', None)):
            if sig is not None:
                try:
                    signal.signal(sig, handle_termination_signal)
                except ValueError:
                    pass

        model = None
        tokenizer = None
        
        # Determine which model to use. An explicit --gguf-model always wins; otherwise
        # let the user pick an installed model or download the default in interactive mode.
        resolved_path = None
        interactive_startup = (not plain_output) and sys.stdin.isatty()
        if args.gguf_model:
            gguf_model_path = args.gguf_model
        elif interactive_startup:
            chosen = select_startup_model(args.ollama_host, "Select Enchan Model")
            if not chosen:
                print("[System] Model selection cancelled.")
                sys.exit(1)
            gguf_model_path = chosen
        else:
            gguf_model_path = args.ollama_model

        # Resolve the chosen model to a direct file or an Ollama blob.
        if gguf_model_path:
            if Path(gguf_model_path).exists():
                resolved_path = gguf_model_path
            else:
                try:
                    from enchan_llama_backend import resolve_ollama_model_to_blob
                    resolved_path, _ = resolve_ollama_model_to_blob(gguf_model_path)
                except Exception:
                    pass

        # Only the designated default model is auto-downloaded. Any other model is
        # assumed to already exist in the user's environment and is used as-is.
        if not resolved_path and gguf_model_path == ENCHAN_DEFAULT_DOWNLOAD_MODEL:
            if not standalone_ollama_pull(gguf_model_path):
                print("[Error] Failed to download the default model. Please specify a valid --gguf-model.")
                sys.exit(1)

        # Use the resolved model for this run. The interactive picker (or an explicit
        # --gguf-model) chooses the model each launch, so it is not persisted to config.
        args.gguf_model = gguf_model_path

        model_name_short = f"enchan:{gguf_model_path}"
    else:
        model = None
        tokenizer = None
        if not ensure_ollama_running(args.ollama_host, auto_start=not args.no_ollama_start, quiet=plain_output):
            if not plain_output:
                print("[Error] Ollama API is not available. Start Ollama manually or check --ollama-host.")
            else:
                print("[Error] Ollama API is not available.")
            return
        # If the configured model is not installed, let the user pick another (or download the default).
        interactive_startup = (not plain_output) and sys.stdin.isatty()
        if interactive_startup:
            installed = list_installed_ollama_models(args.ollama_host)
            if args.ollama_model not in installed:
                chosen = select_startup_model(args.ollama_host, "Select Ollama Model")
                if not chosen:
                    print("[System] Model selection cancelled.")
                    return
                if chosen not in installed and not standalone_ollama_pull(chosen):
                    print("[Error] Failed to download the selected model.")
                    return
                args.ollama_model = chosen
                local_cfg["ollama_model"] = chosen
                save_local_config(local_cfg)
        model_name_short = f"ollama:{args.ollama_model}"
    
    if not plain_output:
        active_model_disp = MODEL_ID if backend_mode == 'hf' else (args.gguf_model if (backend_mode == 'enchan' and args.gguf_model) else args.ollama_model)
        print(f"  * Selected Model: {active_model_disp}")
        print("  * Type 'exit' to close.")
        print("  * Type '/help' to show CLI commands.")
        if agent_mode:
            print("  * Agent mode enabled: ReAct tool calls will be executed locally.")
        print("  * Simply type or drag-and-drop a file/directory path to analyze and compress it!")
        print("-" * 70)

    session_id = uuid.uuid4().hex
    session_log_path = new_session_log_path()
    append_session_event(
        session_log_path,
        {
            "type": "session_start",
            "session_id": session_id,
            "model": MODEL_ID if backend_mode == "hf" else args.ollama_model,
            "backend": backend_mode,
            "log_path": str(session_log_path),
            "agent_mode": agent_mode,
        },
    )
    ensure_memory_dirs()
    startup_memory_context = load_memory_context()
    append_session_event(
        session_log_path,
        {
            "type": "memory_loaded",
            "chars": len(startup_memory_context),
            "source": str(CLI_DIR / "memory"),
            "sources": ["guidelines", "knowledge"],
        },
    )
    if startup_memory_context and not plain_output:
        print(f"[System] Loaded local memory: {len(startup_memory_context):,} chars from {CLI_DIR / 'memory' / 'guidelines'} and {CLI_DIR / 'memory' / 'knowledge'}")

    def record_memory(reason: str) -> None:
        return None

    def consolidate_memory(reason: str) -> None:
        return None
    try:
        tokenizer = load_enchan_tokenizer_for_ollama()
    except Exception as e:
        if not plain_output:
            print(f"[Warning] Failed to load tokenizer for precise token counting: {e}")
        tokenizer = None

    chat_history = []
    file_context = ""
    source_token_count = 0
    loaded_files = []
    
    single_turn_prompt = None
    if args.ask_file:
        ask_path = Path(args.ask_file)
        if not ask_path.is_absolute():
            ask_path = (Path.cwd() / ask_path).resolve()
        try:
            single_turn_prompt = ask_path.read_text(encoding="utf-8")
        except Exception as e:
            append_session_event(session_log_path, {"type": "error", "stage": "ask_file_read", "path": str(ask_path), "message": str(e)})
            print(f"[Error] Failed to read --ask-file: {e}")
            return
    elif args.ask:
        single_turn_prompt = args.ask

    # Initialize prompt_toolkit only for interactive mode.
    session = None
    if PROMPT_TOOLKIT_AVAILABLE and single_turn_prompt is None:
        kb = KeyBindings()

        slash_commands = (
            "/resume", "/compress", "/model", "/status", "/set",
            "/help", "/new", "/exit",
        )

        @kb.add('/')
        def _(event):
            buffer = event.current_buffer
            start_of_input = not buffer.document.text_before_cursor
            buffer.insert_text('/')
            if start_of_input:
                buffer.start_completion(select_first=False)

        @kb.add('enter')  # Standard Enter is triggered (captures both Enter and Shift+Enter at terminal level)
        def _(event):
            buffer = event.current_buffer
            if buffer.complete_state and buffer.complete_state.current_completion:
                completion = buffer.complete_state.current_completion
                buffer.apply_completion(completion)
                if str(completion.text).startswith("/"):
                    buffer.validate_and_handle()
                return

            text = buffer.text.strip()
            if text.startswith("/") and " " not in text:
                matches = [cmd for cmd in slash_commands if cmd.startswith(text)]
                if len(matches) == 1 and matches[0] != text:
                    buffer.text = matches[0]
                    buffer.cursor_position = len(buffer.text)
                    buffer.validate_and_handle()
                    return

            import ctypes
            is_shift = False
            try:
                # Use GetAsyncKeyState to query global physical key state (VK_SHIFT = 0x10), bypassing thread/window focus limits.
                is_shift = (ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000) != 0
            except Exception:
                pass

            if is_shift:
                # Shift+Enter: Break line and grow input box
                buffer.insert_text('\n')
            else:
                # Standard Enter: Submit the prompt immediately!
                buffer.validate_and_handle()

        @kb.add('tab')
        def _(event):
            buffer = event.current_buffer
            if buffer.complete_state and buffer.complete_state.current_completion:
                buffer.apply_completion(buffer.complete_state.current_completion)
            else:
                buffer.start_completion(select_first=True)


        @kb.add('c-j')              # Ctrl+Enter inserts newline (Break line)
        def _(event):
            event.current_buffer.insert_text('\n')

        style = make_prompt_style()

        from prompt_toolkit.completion import Completer, Completion

        class EnchanCompleter(Completer):
            def __init__(self):
                # Nested command structure with (description, sub_commands_dict)
                # Ordered by frequency of use for better UX
                self.completions = {
                    "/resume": ("List resumable sessions or resume a specific session", None),
                    "/compress": ("Optimize older conversation turns", None),
                    "/model": ("Switch the active model", None),
                    "/status": ("Show model, history, context, and generation settings", None),
                    "/set": ("Configure generation and early exit parameters", {
                        "temp": ("Set sampling temperature, e.g., /set temp 0.7", None),
                        "top_p": ("Set nucleus sampling threshold, e.g., /set top_p 0.95", None),
                        "top_k": ("Set top_k sampling count, e.g., /set top_k 40", None),
                        "presence": ("Set presence penalty, e.g., /set presence 1.5", None),
                        "yarn": ("Set YaRN scaling factor, e.g., /set yarn 1.0", None),
                        "max": ("Set max generated tokens (-1 for infinite)", None),
                        "input": ("Set max input context tokens allowed", None),
                        "exit_layer": ("Set force early exit layer index (HF only)", None),
                        "exit_thresh": ("Set early exit threshold probability (HF only)", None),
                    }),
                    "/help": ("Show help menu and available commands", None),
                    "/new": ("Start a new session (clears chat history and file context)", None),
                    "/exit": ("Exit the CLI", None),
                }

            def get_completions(self, document, complete_event):
                text = document.text_before_cursor
                # Only autocomplete when starting with "/"
                if not text.startswith("/"):
                    return

                parts = text.split()
                if not parts:
                    return

                # Case 1: Typing the main command (e.g., "/se" -> "/set")
                if len(parts) == 1 and not text.endswith(" "):
                    word = parts[0]
                    for cmd, (desc, _) in self.completions.items():
                        if cmd.startswith(word):
                            yield Completion(cmd, start_position=-len(word), display_meta=desc)
                
                # Case 2: Typing sub-commands (e.g., "/set t" -> "temp")
                elif len(parts) >= 1:
                    cmd = parts[0]
                    if cmd in self.completions:
                        _, sub_dict = self.completions[cmd]
                        if sub_dict:
                            word = parts[1] if (len(parts) > 1 and not text.endswith(" ")) else ""
                            start_pos = -len(word) if word else 0
                            for sub, (sub_desc, _) in sub_dict.items():
                                if not word or sub.startswith(word):
                                    yield Completion(sub, start_position=start_pos, display_meta=sub_desc)

        completer = EnchanCompleter()

        session = PromptSession(
            key_bindings=kb, 
            style=style, 
            completer=completer,
            complete_while_typing=True,
            reserve_space_for_menu=6
        )

    generation_config = {
        "max_input_tokens": int(args.ollama_ctx) if backend_mode in ("ollama", "enchan") else 131072,
        "max_new_tokens": int(args.max_new_tokens) if backend_mode in ("ollama", "enchan") else 4096,
        "temperature": float(args.temperature) if backend_mode in ("ollama", "enchan") else 1.0,
        "top_p": float(args.top_p) if backend_mode in ("ollama", "enchan") else 0.95,
        "top_k": int(args.top_k) if backend_mode in ("ollama", "enchan") else 20,
        "presence_penalty": float(getattr(args, "presence_penalty", 1.5)),
        "enable_thinking": not getattr(args, "no_thinking", False),
        "preserve_thinking": getattr(args, "preserve_thinking", False),
        "yarn_factor": float(getattr(args, "yarn_factor", 1.0)),
        "view_think": bool(args.view_think),
        "do_sample": True,
        "model_id": MODEL_ID if backend_mode == "hf" else (f"enchan:{args.gguf_model}" if backend_mode == "enchan" else f"ollama:{args.ollama_model}"),
        "ollama_model": args.ollama_model if backend_mode == "ollama" else None,
        "ollama_host": args.ollama_host if backend_mode == "ollama" else None,
        "backend": backend_mode,
    }
    
    # Synchronize starting parameters with official model recommendations + JSON overrides
    sync_generation_config_to_active_model(generation_config, active_model_name, backend_mode)
    
    if agent_mode:
        generation_config["temperature"] = 0.1
        generation_config["top_p"] = 1.0
        generation_config["do_sample"] = False

    if single_turn_prompt is not None:
        if backend_mode not in ("ollama", "enchan"):
            append_session_event(session_log_path, {"type": "error", "stage": "single_turn_backend", "backend": backend_mode})
            print("[Error] --ask and --ask-file currently require --backend ollama or --backend enchan.")
            return
        if not single_turn_prompt.strip():
            append_session_event(session_log_path, {"type": "error", "stage": "single_turn_empty_prompt"})
            print("[Error] --ask prompt is empty.")
            return
            

        if backend_mode == "enchan":
            from enchan_llama_backend import run_enchan_llama_once
            memory_context = load_memory_context()
            run_enchan_llama_once(
                single_turn_prompt.strip(),
                chat_history,
                generation_config,
                session_log_path,
                args,
                tokenizer=tokenizer,
                plain=plain_output,
                memory_context=memory_context,
            )
            append_session_event(session_log_path, {"type": "session_end", "reason": "single_turn"})
            record_memory("single_turn")
            return

        memory_context = load_memory_context()
        run_ollama_once(
            single_turn_prompt.strip(),
            chat_history,
            generation_config,
            session_log_path,
            args,
            tokenizer=tokenizer,
            plain=plain_output,
            memory_context=memory_context,
        )
        append_session_event(session_log_path, {"type": "session_end", "reason": "single_turn"})
        record_memory("single_turn")
        return

    while True:
        try:
            auto_compressed = False
            enchan_preload_thread = None
            enchan_preload_result = {"ok": True}
            
            if PROMPT_TOOLKIT_AVAILABLE and session is not None:
                # Dynamic pixel-perfect full-width line with subtle dark gray ANSI color (\x1b[90m)
                width = shutil.get_terminal_size().columns
                print("\n\x1b[90m" + "─" * width + "\x1b[0m")
                print("[You]:")
                user_input = session.prompt("  ", multiline=True, bottom_toolbar=lambda: " ")
            else:
                user_input = input("\n[You]: ")

            user_input = sanitize_for_json(user_input)
            if user_input.strip().lower() in ['exit', 'quit']:
                append_session_event(session_log_path, {"type": "session_end", "reason": user_input.strip().lower()})
                record_memory(user_input.strip().lower())
                print("Exiting...")
                break

            if not user_input.strip():
                continue

            if backend_mode == "enchan" and not user_input.strip().startswith("/"):
                def preload_enchan_engine():
                    try:
                        from enchan_llama_backend import ensure_enchan_llama_for_request
                        enchan_preload_result["ok"] = ensure_enchan_llama_for_request(None, args)
                    except Exception as exc:
                        enchan_preload_result["ok"] = False
                        enchan_preload_result["error"] = str(exc)

                enchan_preload_thread = threading.Thread(
                    target=preload_enchan_engine,
                    name="enchan-llama-preload",
                    daemon=True,
                )
                enchan_preload_thread.start()

            append_session_event(session_log_path, {"type": "input", "content": user_input})
            if user_input.strip().startswith("/"):
                handled, file_context, should_exit = handle_cli_command(
                    user_input,
                    chat_history,
                    file_context,
                    loaded_files,
                    generation_config,
                    session_log_path=session_log_path,
                    agent_mode=agent_mode,
                    memory_recorder=record_memory,
                    tokenizer=tokenizer,
                )
                if should_exit:
                    break
                if handled:
                    backend_mode = generation_config.get("backend", backend_mode)
                    args.backend = backend_mode
                    if generation_config.get("ollama_model"):
                        args.ollama_model = generation_config["ollama_model"]
                    if generation_config.get("ollama_host"):
                        args.ollama_host = generation_config["ollama_host"]
                    if generation_config.get("gguf_model"):
                        args.gguf_model = generation_config["gguf_model"]
                    continue

            if not agent_mode and user_input.strip().lower() == "enchan --agent":
                input_length = count_text_tokens(tokenizer, user_input) if tokenizer is not None else estimate_text_tokens_rough(user_input)
                chat_history.append({"role": "user", "content": user_input})
                append_session_event(
                    session_log_path,
                    {
                        "type": "message",
                        "role": "user",
                        "display_input": user_input,
                        "content": user_input,
                        "input_tokens": input_length,
                        "agent_mode": False,
                    },
                )
                print_response_header(response_label(generation_config), NORMAL_MODE_TOOL_GUIDANCE, line_char="─")
                chat_history.append({"role": "model", "content": NORMAL_MODE_TOOL_GUIDANCE})
                append_session_event(
                    session_log_path,
                    {
                        "type": "message",
                        "role": "model",
                        "content": NORMAL_MODE_TOOL_GUIDANCE,
                        "agent_mode": False,
                        "tool_guidance": True,
                    },
                )
                continue

            print_agent_turn_header(generation_config)
            generation_config["suppress_response_header"] = True

            current_prompt = user_input
            chat_history.append({"role": "user", "content": current_prompt})

            # Universal Auto-Compression for all backends
            max_input_tokens = int(generation_config["max_input_tokens"])
            # Only consider compression if history is somewhat established
            if len(chat_history) > 6:
                # Estimate total tokens of current history
                preflight_prompt = tokenizer.apply_chat_template(chat_history, add_generation_prompt=True, tokenize=False) if tokenizer is not None else current_prompt
                estimated_total = count_text_tokens(tokenizer, preflight_prompt) if tokenizer is not None else estimate_text_tokens_rough(current_prompt) * len(chat_history)
                
                # Trigger compression closer to the actual limits rather than an arbitrary 32K cap.
                # Leave a 15% buffer for the new prompt and generation output.
                compression_threshold = int(max_input_tokens * 0.85)
                
                if estimated_total > compression_threshold:
                    # Dynamically preserve more recent turns to avoid breaking the conversational flow.
                    # Instead of a hardcoded 4, we keep a larger sliding window (e.g. 10 messages).
                    dynamic_keep_turns = min(10, len(chat_history) - 2)
                    chat_history = compress_chat_history(chat_history, tokenizer=tokenizer, keep_turns=dynamic_keep_turns)

            if backend_mode in ("hf", "ollama", "enchan"):
                memory_context = load_memory_context()
                system_context = build_memory_prompt_section(memory_context)
                if system_context:
                     generation_config["system_context"] = f"{AGENT_SYSTEM_PROMPT}{system_context}"
                else:
                     generation_config["system_context"] = AGENT_SYSTEM_PROMPT

            if backend_mode == "enchan":
                input_length = count_text_tokens(tokenizer, current_prompt) if tokenizer is not None else estimate_text_tokens_rough(current_prompt)
                
                if input_length > max_input_tokens:
                    chat_history.pop()
                    print(
                        f"[Error] Prompt is {format_count(input_length)} tokens, "
                        f"which exceeds the local safety limit of {format_count(max_input_tokens)} tokens."
                    )
                    continue
                append_session_event(
                    session_log_path,
                    {
                        "type": "message",
                        "role": "user",
                        "display_input": user_input,
                        "content": current_prompt,
                        "input_tokens_estimate": input_length,
                        "backend": "enchan",
                    },
                )
                if enchan_preload_thread is not None:
                    enchan_preload_thread.join()
                    if not enchan_preload_result.get("ok", False):
                        err_msg = enchan_preload_result.get("error", "Failed to start engine")
                        print(f"[Error] Engine preload failed: {err_msg}")
                        append_session_event(
                            session_log_path,
                            {
                                "type": "error",
                                "stage": "enchan_llama_preload",
                                "message": err_msg,
                            },
                        )
                        continue
                from enchan_llama_backend import run_enchan_llama_agent_turn
                run_enchan_llama_agent_turn(chat_history, generation_config, session_log_path, args, tokenizer=tokenizer)
                consolidate_memory("active_turn")
                continue

            if backend_mode == "ollama":
                input_length = count_text_tokens(tokenizer, current_prompt) if tokenizer is not None else estimate_text_tokens_rough(current_prompt)
                
                if input_length > max_input_tokens:
                    chat_history.pop()
                    print(
                        f"[Error] Prompt is {format_count(input_length)} tokens, "
                        f"which exceeds the local safety limit of {format_count(max_input_tokens)} tokens."
                    )
                    continue
                append_session_event(
                    session_log_path,
                    {
                        "type": "message",
                        "role": "user",
                        "display_input": user_input,
                        "content": current_prompt,
                        "input_tokens_estimate": input_length,
                        "backend": "ollama",
                    },
                )
                run_ollama_agent_turn(chat_history, generation_config, session_log_path, args, tokenizer=tokenizer)
                consolidate_memory("active_turn")
                continue

        except KeyboardInterrupt:
            append_session_event(session_log_path, {"type": "session_end", "reason": "keyboard_interrupt"})
            record_memory("keyboard_interrupt")
            print("\n[System] Interrupted by user. Exiting...")
            break
        except Exception as e:
            append_session_event(session_log_path, {"type": "error", "stage": "main_loop", "message": str(e)})
            print(f"\n[Error] {e}")

if __name__ == "__main__":
    main()


