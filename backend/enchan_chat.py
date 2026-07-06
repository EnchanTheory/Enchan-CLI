import os
import sys
import logging
from pathlib import Path

# --- Path Resolution for Imports ---
BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

# Suppress Hugging Face, Transformers, and Hub console warnings to keep CLI output pristine
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

import uuid

from backend.interactive_input import create_interactive_session

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


from backend.session_log import (
    append_session_event,
    new_session_log_path,
)
from backend.tokenizer_bridge import load_enchan_tokenizer_for_ollama
from backend.ollama_registry import (
    standalone_ollama_pull,
    list_installed_ollama_models,
    ENCHAN_DEFAULT_DOWNLOAD_MODEL,
)
from backend.startup_selection import (
    select_startup_backend,
    select_startup_model,
)
from backend.cli_args import parse_args

MODEL_ID = "google/gemma-4-e2b-it"

from backend.context_compression import COSMIC_AVAILABLE
from backend.ollama_backend import ensure_ollama_running
from backend.memory_store import (
    ensure_memory_dirs,
    load_memory_context,
)
from backend.ui_theme import (
    ANSI_GOLD,
    ANSI_RESET,
)

from backend.core.config import load_local_config, save_local_config
from backend.runtime_config import sync_generation_config_to_active_model
from backend.chat_loop import KNOWN_SLASH_COMMANDS, run_chat_loop

if not COSMIC_AVAILABLE:
    print("[Warning] Could not load Enchan Engine DLL. External context compression will be disabled.")


def main():
    local_cfg = load_local_config()

    # 1. Parse Arguments via modern modular CLI Args parser
    args = parse_args()
    
    backend_explicit = any(arg == "--backend" or arg.startswith("--backend=") for arg in sys.argv[1:])
    single_turn_requested = bool(args.ask or args.ask_file)
    if not backend_explicit and not single_turn_requested and sys.stdin.isatty():
        args.backend = select_startup_backend(args.backend)
        
    # Dynamic defaults based on official Ollama Modelfile parameters
    active_model_name = args.gguf_model if args.backend == "enchan" and args.gguf_model else args.ollama_model
    if active_model_name:
        try:
            from backend.enchan_llama_backend import resolve_ollama_model_to_blob
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
        from backend.enchan_llama_backend import shutdown_enchan_llama
        atexit.register(shutdown_enchan_llama)

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

        resolved_path = None
        interactive_startup = (not single_turn_requested) and sys.stdin.isatty()
        if args.gguf_model:
            gguf_model_path = args.gguf_model
        elif interactive_startup:
            chosen = select_startup_model(args.ollama_host, "Select Enchan Model", filter_gguf=True)
            if not chosen:
                print("[System] Model selection cancelled.")
                sys.exit(1)
            gguf_model_path = chosen
        else:
            gguf_model_path = args.ollama_model

        if gguf_model_path:
            if Path(gguf_model_path).exists():
                resolved_path = gguf_model_path
            else:
                try:
                    from backend.enchan_llama_backend import resolve_ollama_model_to_blob
                    resolved_path, _ = resolve_ollama_model_to_blob(gguf_model_path)
                except Exception:
                    pass

        if not resolved_path and gguf_model_path == ENCHAN_DEFAULT_DOWNLOAD_MODEL:
            if not standalone_ollama_pull(gguf_model_path):
                print("[Error] Failed to download the default model. Please specify a valid --gguf-model.")
                sys.exit(1)

        args.gguf_model = gguf_model_path
    else:
        if not ensure_ollama_running(args.ollama_host, auto_start=not args.no_ollama_start, quiet=plain_output):
            if not plain_output:
                print("[Error] Ollama API is not available. Start Ollama manually or check --ollama-host.")
            else:
                print("[Error] Ollama API is not available.")
            return
            
        interactive_startup = (not single_turn_requested) and sys.stdin.isatty()
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
    
    if not plain_output:
        update_notice_path = CLI_DIR / ".enchan-update-available"
        if update_notice_path.exists():
            update_notice_path.unlink(missing_ok=True)
            print(f"  {ANSI_GOLD}[Info] Update available. Run: enchan update{ANSI_RESET}")
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

    session = None
    if single_turn_prompt is None:
        session = create_interactive_session(tuple(sorted(KNOWN_SLASH_COMMANDS)))

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
        "max_obs_chars": load_local_config().get("max_obs_chars", 10000),
    }
    
    sync_generation_config_to_active_model(generation_config, active_model_name, backend_mode)
    
    # Re-apply explicit command-line overrides to prevent them from being wiped out by sync logic
    explicit_overrides = getattr(args, "explicit_overrides", {})
    if "temperature" in explicit_overrides:
        generation_config["temperature"] = explicit_overrides["temperature"]
    if "top_p" in explicit_overrides:
        generation_config["top_p"] = explicit_overrides["top_p"]
    if "top_k" in explicit_overrides:
        generation_config["top_k"] = explicit_overrides["top_k"]
    if "presence_penalty" in explicit_overrides:
        generation_config["presence_penalty"] = explicit_overrides["presence_penalty"]
    if "yarn_factor" in explicit_overrides:
        generation_config["yarn_factor"] = explicit_overrides["yarn_factor"]
    if "max_new_tokens" in explicit_overrides:
        generation_config["max_new_tokens"] = explicit_overrides["max_new_tokens"]
    if "ollama_ctx" in explicit_overrides:
        generation_config["max_input_tokens"] = explicit_overrides["ollama_ctx"]
    
    if agent_mode:
        generation_config["temperature"] = 0.1
        generation_config["top_p"] = 1.0
        generation_config["do_sample"] = False

    if single_turn_prompt is not None:
        from backend.one_shot import execute_single_turn
        execute_single_turn(
            single_turn_prompt,
            backend_mode,
            session_log_path,
            chat_history,
            generation_config,
            args,
            tokenizer=tokenizer,
            plain_output=plain_output,
        )
        return

    run_chat_loop(
        session=session,
        backend_mode=backend_mode,
        args=args,
        session_log_path=session_log_path,
        chat_history=chat_history,
        file_context=file_context,
        loaded_files=loaded_files,
        generation_config=generation_config,
        agent_mode=agent_mode,
        tokenizer=tokenizer,
    )

if __name__ == "__main__":
    main()
