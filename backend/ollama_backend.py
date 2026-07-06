import json
import sys
import subprocess
import time
import urllib.error
import urllib.request
import shutil
import re
from pathlib import Path
from typing import Optional

from backend.ui_theme import print_agent_action, print_agent_observation, get_spinner_status

try:
    import msvcrt
except ImportError:
    msvcrt = None

# Path Resolution
BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent


from backend.session_log import append_session_event
from backend.agent_tools import AGENT_SYSTEM_PROMPT
from backend.agent_loop import run_agent_loop
from backend.memory_store import build_memory_prompt_section
from backend.agent_tools_schema import AGENT_TOOLS_SCHEMA

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "gemma4:e2b-it-qat"

# --- Local Helpers to prevent circular imports ---
def sanitize_for_json(text: str) -> str:
    return text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")

def strip_thought_blocks(text: str) -> str:
    """Removes <thought>...</thought> and <think>...</think> blocks to keep multi-turn context clean."""
    if not text:
        return text
    text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()

def format_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)

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

def count_text_tokens(tokenizer, text: str) -> int:
    if tokenizer is None or not text:
        return 0
    return len(tokenizer.encode(text, add_special_tokens=False))

def build_agent_goal_prompt(goal: str, memory_context: str = "") -> str:
    memory_section = build_memory_prompt_section(memory_context)
    return f"{AGENT_SYSTEM_PROMPT}{memory_section}\n\nGoal:\n{goal}"

def append_tool_result_event(session_log_path: Path, result: dict, iteration: int, backend: Optional[str] = None):
    event = result.get("event")
    if not isinstance(event, dict):
        return
    payload = dict(event)
    payload["iteration"] = iteration
    if backend:
        payload["backend"] = backend
    append_session_event(session_log_path, payload)


def esc_pressed() -> bool:
    if msvcrt is None:
        return False
    pressed = False
    while msvcrt.kbhit():
        key = msvcrt.getwch()
        if key == "\x1b":
            pressed = True
    return pressed


# --- Ollama API Operations ---
def ollama_api_available(host: str) -> bool:
    try:
        with urllib.request.urlopen(host.rstrip("/") + "/api/version", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def ensure_ollama_running(host: str, auto_start: bool = True, quiet: bool = False) -> bool:
    if ollama_api_available(host):
        return True
    if not auto_start:
        return False

    if not quiet:
        print("[System] Ollama API is not responding. Starting `ollama serve` in the background...")
    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except Exception as e:
        if not quiet:
            print(f"[Error] Failed to start Ollama: {e}")
        return False

    for _ in range(30):
        time.sleep(0.5)
        if ollama_api_available(host):
            if not quiet:
                print("[System] Ollama API is ready.")
            return True
    return False


def generate_ollama_response(
    chat_history: list[dict],
    generation_config: dict,
    session_log_path,
    ollama_host: str,
    ollama_model: str,
    view_think: bool = False,
    stream_output: bool = True,
    show_metrics: bool = True,
) -> dict | None:
    api_url = ollama_host.rstrip("/") + "/api/chat"
    messages = []
    system_context = generation_config.get("system_context")
    if system_context:
        messages.append({
            "role": "system",
            "content": sanitize_for_json(system_context),
        })

    for msg in chat_history:
        role = msg.get("role")
        if role in ("assistant", "model"):
            item = {
                "role": "assistant",
                "content": sanitize_for_json(msg.get("content", "")) or "",
            }
            if "tool_calls" in msg:
                item["tool_calls"] = msg["tool_calls"]
            messages.append(item)
        elif role == "system":
            messages.append({
                "role": "system",
                "content": sanitize_for_json(msg.get("content", ""))
            })
        elif role == "tool":
            messages.append({
                "role": "tool",
                "content": sanitize_for_json(msg.get("content", ""))
            })
        else:
            messages.append({
                "role": "user",
                "content": sanitize_for_json(msg.get("content", ""))
            })
    payload = {
        "model": ollama_model,
        "messages": messages,
        "stream": True,
        "think": True,
        "options": {
            "temperature": float(generation_config["temperature"]),
            "top_p": float(generation_config["top_p"]),
            "top_k": int(generation_config["top_k"]),
            "num_predict": int(generation_config["max_new_tokens"]),
            "num_ctx": int(generation_config["max_input_tokens"]),
        },
        "tools": AGENT_TOOLS_SCHEMA,
    }

    if stream_output and not generation_config.get("suppress_response_header", False):
        width = shutil.get_terminal_size().columns
        print("\n\x1b[90m" + "-" * width + "\x1b[0m")
        print(f"[Enchan:{ollama_model}]:\n", end="", flush=True)

    start_time = time.perf_counter()
    content_parts: list[str] = []
    thinking_parts: list[str] = []
    thinking_started = False
    content_started = False
    final_chunk = {}
    cancelled = False
    printed_len = 0
    tool_calls_merged = []

    status = None
    if stream_output:
        status = get_spinner_status()
        if hasattr(status, "start"):
            status.start()

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw_line in resp:
                if esc_pressed():
                    cancelled = True
                    break
                if not raw_line.strip():
                    continue
                chunk = json.loads(raw_line.decode("utf-8"))
                final_chunk = chunk
                message = chunk.get("message") or {}
                thinking = message.get("thinking") or ""
                content = message.get("content") or ""

                if thinking:
                    thinking_parts.append(thinking)
                    if stream_output and view_think:
                        if status is not None:
                            status.stop()
                            status = None
                        if not thinking_started:
                            print("\x1b[2;90m", end="", flush=True)
                            thinking_started = True
                        print(thinking, end="", flush=True)

                if content:
                    content_parts.append(content)
                    if stream_output:
                        if thinking_started and not content_started and status is None:
                            if view_think:
                                print("\x1b[0m", end="", flush=True)
                        content_started = True

                        if status is not None:
                            status.stop()
                            status = None
                        print(content, end="", flush=True)

                if "tool_calls" in message:
                    for i, tc in enumerate(message["tool_calls"]):
                        if i >= len(tool_calls_merged):
                            tool_calls_merged.append({"function": {"name": "", "arguments": {}}})
                        
                        func_chunk = tc.get("function", {})
                        if "name" in func_chunk and func_chunk["name"]:
                            tool_calls_merged[i]["function"]["name"] = func_chunk["name"]
                        
                        args_chunk = func_chunk.get("arguments", {})
                        for k, v in args_chunk.items():
                            if k not in tool_calls_merged[i]["function"]["arguments"]:
                                tool_calls_merged[i]["function"]["arguments"][k] = v
                            else:
                                if isinstance(v, str) and isinstance(tool_calls_merged[i]["function"]["arguments"][k], str):
                                    tool_calls_merged[i]["function"]["arguments"][k] += v
                                else:
                                    tool_calls_merged[i]["function"]["arguments"][k] = v
                if esc_pressed():
                    cancelled = True
                    break
    except urllib.error.HTTPError as e:
        if status is not None:
            status.stop()
        body = e.read().decode("utf-8", errors="replace")
        if stream_output or show_metrics:
            print(f"\n[Error] Ollama HTTP error {e.code}: {body}")
        append_session_event(session_log_path, {"type": "error", "stage": "ollama_http", "status": e.code, "body": body})
        return None
    except Exception as e:
        if status is not None:
            status.stop()
        if stream_output or show_metrics:
            print(f"\n[Error] Ollama request failed: {e}")
        append_session_event(session_log_path, {"type": "error", "stage": "ollama_request", "message": str(e)})
        return None

    elapsed = time.perf_counter() - start_time
    response = "".join(content_parts)
    thinking = "".join(thinking_parts)
    if status is not None:
        status.stop()
    eval_count = int(final_chunk.get("eval_count") or 0)
    eval_duration_ns = int(final_chunk.get("eval_duration") or 0)
    tps = (eval_count / (eval_duration_ns / 1_000_000_000)) if eval_count and eval_duration_ns else 0.0

    if cancelled:
        if stream_output:
            print("\n\x1b[2;90m[System] Ollama generation cancelled by Esc.\x1b[0m")
        append_session_event(
            session_log_path,
            {
                "type": "generation_cancelled",
                "backend": "ollama",
                "model": ollama_model,
                "content": response,
                "thinking": thinking,
                "tool_calls": tool_calls_merged,
                "elapsed_sec": elapsed,
                "eval_count": eval_count,
            },
        )
        return {
            "cancelled": True,
            "response": response,
            "thinking": thinking,
            "tool_calls": tool_calls_merged,
            "output_tokens": eval_count,
            "elapsed_sec": elapsed,
            "tps": tps,
        }

    if stream_output:
        if thinking_started and not content_started:
            print("\x1b[0m")
        else:
            print()
    if show_metrics:
        if tps > 0:
            print(f"\x1b[2;90m[Metrics] Ollama eval: {eval_count} tok @ {tps:.1f} t/s | wall: {elapsed:.2f}s\x1b[0m")
        else:
            print(f"\x1b[2;90m[System] Ollama response completed in {elapsed:.2f}s\x1b[0m")

    append_session_event(
        session_log_path,
        {
            "type": "ollama_generation",
            "model": ollama_model,
            "content": response,
            "thinking": thinking,
            "tool_calls": tool_calls_merged,
            "elapsed_sec": elapsed,
            "eval_count": eval_count,
            "eval_duration_ns": eval_duration_ns,
            "tps": tps,
        },
    )
    return {
        "response": response,
        "thinking": thinking,
        "tool_calls": tool_calls_merged,
        "output_tokens": eval_count,
        "elapsed_sec": elapsed,
        "tps": tps,
    }


# --- Ollama ReAct Agent Loops ---
def run_ollama_once(
    prompt: str,
    chat_history: list[dict],
    generation_config: dict,
    session_log_path: Path,
    args,
    tokenizer=None,
    plain: bool = False,
    memory_context: str = "",
) -> None:
    current_prompt = build_agent_goal_prompt(prompt, memory_context)
    chat_history.append({"role": "user", "content": current_prompt})
    input_length = count_text_tokens(tokenizer, current_prompt) if tokenizer is not None else estimate_text_tokens_rough(current_prompt)
    max_input_tokens = int(generation_config["max_input_tokens"])
    if input_length > max_input_tokens:
        chat_history.pop()
        append_session_event(
            session_log_path,
            {
                "type": "error",
                "stage": "single_turn_input_safety_limit",
                "prompt_tokens_estimate": input_length,
                "max_input_tokens": max_input_tokens,
                "backend": "ollama",
            },
        )
        print(
            f"[Error] Prompt is {format_count(input_length)} tokens, "
            f"which exceeds the local safety limit of {format_count(max_input_tokens)} tokens."
        )
        return

    append_session_event(
        session_log_path,
        {
            "type": "message",
            "role": "user",
            "display_input": prompt,
            "content": current_prompt,
            "input_tokens_estimate": input_length,
            "backend": "ollama",
            "single_turn": True,
        },
    )

    run_agent_loop(
        chat_history=chat_history,
        generation_config=generation_config,
        session_log_path=session_log_path,
        backend="ollama",
        generate_response=lambda: generate_ollama_response(
            chat_history,
            generation_config,
            session_log_path,
            args.ollama_host,
            generation_config.get("ollama_model", args.ollama_model),
            view_think=bool(generation_config.get("view_think", False)),
            stream_output=not plain,
            show_metrics=not plain,
        ),
        append_tool_result_event=append_tool_result_event,
        tokenizer=tokenizer,
        plain=plain,
        single_turn=True,
        strip_final_thoughts=False,
        print_plain_final=True,
    )


def run_ollama_agent_turn(
    chat_history: list[dict],
    generation_config: dict,
    session_log_path: Path,
    args,
    tokenizer=None,
) -> None:
    run_agent_loop(
        chat_history=chat_history,
        generation_config=generation_config,
        session_log_path=session_log_path,
        backend="ollama",
        generate_response=lambda: generate_ollama_response(
            chat_history,
            generation_config,
            session_log_path,
            args.ollama_host,
            generation_config.get("ollama_model", args.ollama_model),
            view_think=bool(generation_config.get("view_think", False)),
        ),
        append_tool_result_event=append_tool_result_event,
        tokenizer=tokenizer,
    )

