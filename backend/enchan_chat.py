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
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))


from session_log import (
    append_session_event,
    list_session_logs,
    load_session_messages,
    new_session_log_path,
    resolve_session_log,
    get_session_metadata,
)

# --- New Modular Zen Imports ---
from backend.tokenizer_bridge import (
    estimate_text_tokens_rough,
    count_text_tokens,
    RunningModelTokenizer,
    load_enchan_tokenizer_for_ollama,
)
from backend.ollama_registry import (
    format_size,
    standalone_ollama_pull,
    list_installed_ollama_models,
    ENCHAN_DEFAULT_DOWNLOAD_MODEL,
    ENCHAN_DEFAULT_DOWNLOAD_SIZE,
)
from backend.startup_selection import (
    select_startup_backend,
    select_startup_model,
)
from backend.thinking import strip_thought_blocks
from backend.cli_args import parse_args

MODEL_ID = "google/gemma-4-e2b-it"


def sanitize_for_json(text: str) -> str:
    return text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")

def format_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


from reading_agent import execute_reading_pipeline
from context_compression import (
    COSMIC_AVAILABLE,
    compress_context,
    compress_chat_history,
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
from ui_theme import (
    interactive_menu,
    make_prompt_style,
    print_python_execution,
    print_python_timeout,
    print_response_header,
    ANSI_GOLD,
    ANSI_RESET,
)

from cli_commands import (
    load_local_config,
    save_local_config,
    sync_generation_config_to_active_model,
    handle_cli_command,
)

KNOWN_SLASH_COMMANDS = frozenset({
    "/resume", "/compress", "/model", "/status", "/set",
    "/help", "/license", "/new", "/exit", "/quit", "/delegate",
})


def first_input_token(user_input: str) -> str:
    stripped = user_input.strip()
    if not stripped:
        return ""
    return stripped.split(maxsplit=1)[0].lower()


def is_known_slash_command(user_input: str) -> bool:
    return first_input_token(user_input) in KNOWN_SLASH_COMMANDS

if not COSMIC_AVAILABLE:
    print("[Warning] Could not load Enchan Engine DLL. External context compression will be disabled.")


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


def response_model_label(generation_config: dict) -> str:
    backend_mode = generation_config.get("backend", "enchan")
    if backend_mode == "enchan":
        val = generation_config.get("gguf_model") or "Local GGUF"
    else:
        val = generation_config.get("ollama_model") or "Ollama API"
    return str(val)


def response_backend_label(generation_config: dict) -> str:
    return str(generation_config.get("backend", "enchan"))


def response_label(generation_config: dict) -> str:
    return f"{response_backend_label(generation_config)}:{response_model_label(generation_config)}"


def print_agent_turn_header(generation_config: dict) -> None:
    pass


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

        if gguf_model_path:
            if Path(gguf_model_path).exists():
                resolved_path = gguf_model_path
            else:
                try:
                    from enchan_llama_backend import resolve_ollama_model_to_blob
                    resolved_path, _ = resolve_ollama_model_to_blob(gguf_model_path)
                except Exception:
                    pass

        if not resolved_path and gguf_model_path == ENCHAN_DEFAULT_DOWNLOAD_MODEL:
            if not standalone_ollama_pull(gguf_model_path):
                print("[Error] Failed to download the default model. Please specify a valid --gguf-model.")
                sys.exit(1)

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
    if PROMPT_TOOLKIT_AVAILABLE and single_turn_prompt is None:
        kb = KeyBindings()
        slash_commands = tuple(sorted(KNOWN_SLASH_COMMANDS))

        @kb.add('/')
        def _(event):
            buffer = event.current_buffer
            start_of_input = not buffer.document.text_before_cursor
            buffer.insert_text('/')
            if start_of_input:
                buffer.start_completion(select_first=False)

        @kb.add('enter')
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
                is_shift = (ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000) != 0
            except Exception:
                pass

            if is_shift:
                buffer.insert_text('\n')
            else:
                buffer.validate_and_handle()

        @kb.add('tab')
        def _(event):
            buffer = event.current_buffer
            if buffer.complete_state and buffer.complete_state.current_completion:
                buffer.apply_completion(buffer.complete_state.current_completion)
            else:
                buffer.start_completion(select_first=True)

        @kb.add('c-j')
        def _(event):
            event.current_buffer.insert_text('\n')

        style = make_prompt_style()

        from prompt_toolkit.completion import Completer, Completion

        class EnchanCompleter(Completer):
            def __init__(self):
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
                    "/license": ("Show repository license terms", None),
                    "/new": ("Start a new session (clears chat history and file context)", None),
                    "/exit": ("Exit the CLI", None),
                }

            def get_completions(self, document, complete_event):
                text = document.text_before_cursor
                if not text.startswith("/"):
                    return

                parts = text.split()
                if not parts:
                    return

                if len(parts) == 1 and not text.endswith(" "):
                    word = parts[0]
                    for cmd, (desc, _) in self.completions.items():
                        if cmd.startswith(word):
                            yield Completion(cmd, start_position=-len(word), display_meta=desc)
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

            if backend_mode == "enchan" and not is_known_slash_command(user_input):
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
            if is_known_slash_command(user_input):
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

            max_input_tokens = int(generation_config["max_input_tokens"])
            if len(chat_history) > 6:
                preflight_prompt = tokenizer.apply_chat_template(chat_history, add_generation_prompt=True, tokenize=False) if tokenizer is not None else current_prompt
                estimated_total = count_text_tokens(tokenizer, preflight_prompt) if tokenizer is not None else estimate_text_tokens_rough(current_prompt) * len(chat_history)
                
                compression_threshold = int(max_input_tokens * 0.85)
                
                if estimated_total > compression_threshold:
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
