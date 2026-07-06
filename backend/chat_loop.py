import re
import sys
import shutil
import threading
from pathlib import Path

from backend.session_log import append_session_event
from backend.cli_commands import handle_cli_command
from backend.context_compression import count_text_tokens, compress_chat_history
from backend.tokenizer_bridge import estimate_text_tokens_rough
from backend.memory_store import load_memory_context, build_memory_prompt_section
from backend.enchan_llama_backend import run_enchan_llama_agent_turn
from backend.ollama_backend import run_ollama_agent_turn
from backend.ui_theme import print_response_header

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


def sanitize_for_json(text: str) -> str:
    return text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")


def format_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def response_model_label(generation_config: dict) -> str:
    backend_mode = generation_config.get("backend", "enchan")
    if backend_mode == "enchan":
        model_id = generation_config.get("model_id", "")
        if model_id.startswith("enchan:"):
            import os
            return os.path.basename(model_id[7:])
        return generation_config.get("gguf_model") or "Local GGUF"
    else:
        val = generation_config.get("ollama_model") or "Ollama API"
    return str(val)


def response_backend_label(generation_config: dict) -> str:
    return str(generation_config.get("backend", "enchan"))


def response_label(generation_config: dict) -> str:
    return f"{response_backend_label(generation_config)}:{response_model_label(generation_config)}"


def print_agent_turn_header(generation_config: dict) -> None:
    print_response_header(response_label(generation_config))


def run_chat_loop(
    session,
    backend_mode: str,
    args,
    session_log_path: Path,
    chat_history: list,
    file_context: str,
    loaded_files: list,
    generation_config: dict,
    agent_mode: bool,
    tokenizer,
) -> None:
    """Runs the main interactive chat loop, driving prompts, completions, and model turns."""
    
    def record_memory(reason: str) -> None:
        return None

    def consolidate_memory(reason: str) -> None:
        return None

    while True:
        try:
            auto_compressed = False
            enchan_preload_thread = None
            enchan_preload_result = {"ok": True}
            
            if session is not None:
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
                        from backend.enchan_llama_backend import ensure_enchan_llama_for_request
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
                from backend.agent_tools import NORMAL_MODE_TOOL_GUIDANCE
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
            images = []
            try:
                from backend.source_loader import find_and_encode_images
                images = find_and_encode_images(user_input)
            except Exception:
                pass
            
            user_msg = {"role": "user", "content": current_prompt}
            if images:
                user_msg["images"] = images
                print(f"  \x1b[90m[Vision] Loaded {len(images)} image(s) from prompt context.\x1b[0m")
            chat_history.append(user_msg)

            max_input_tokens = int(generation_config["max_input_tokens"])
            if len(chat_history) > 6:
                preflight_prompt = tokenizer.apply_chat_template(chat_history, add_generation_prompt=True, tokenize=False) if tokenizer is not None else current_prompt
                estimated_total = count_text_tokens(tokenizer, preflight_prompt) if tokenizer is not None else estimate_text_tokens_rough(current_prompt) * len(chat_history)
                compression_threshold = int(max_input_tokens * 0.85)

                if estimated_total > compression_threshold:
                    dynamic_keep_turns = min(10, len(chat_history) - 2)
                    chat_history = compress_chat_history(chat_history, tokenizer=tokenizer, keep_turns=dynamic_keep_turns)

            if backend_mode in ("hf", "ollama", "enchan"):
                from backend.agent_tools import AGENT_SYSTEM_PROMPT
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
