"""Generation entry points with a cross-platform Esc cancel path.

This module keeps the low-level terminal input handling out of the backend
request code while preserving the existing public run_* entry points used by the
chat loop and one-shot mode.
"""

from __future__ import annotations

import json
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from backend.agent_tools_schema import get_agent_tools_schema
from backend.generation_cancel import GenerationInputGuard, esc_pressed
from backend.thinking import split_thought_blocks

import backend.enchan_llama_backend as enchan_base
import backend.ollama_backend as ollama_base


# Patch the Ollama backend's module-level poller.  Unlike the Enchan llama
# backend, Ollama keeps esc_pressed at module scope, so this avoids duplicating
# its generation code while still giving it the same macOS/Linux behavior.
ollama_base.esc_pressed = esc_pressed


def generate_enchan_llama_response(
    chat_history: list[dict],
    generation_config: dict,
    session_log_path: Path,
    host: str = enchan_base.DEFAULT_ENCHAN_LLAMA_HOST,
    stream_output: bool = True,
    show_metrics: bool = True,
    chunk_callback: Optional[Callable[[str], None]] = None,
) -> dict | None:
    """Stream from the Enchan llama.cpp server with Esc cancellation on all OSes."""

    from backend.ui_theme import get_spinner_status

    api_url = host.rstrip("/") + "/v1/chat/completions"
    messages = []

    system_context = generation_config.get("system_context")
    if system_context:
        messages.append({"role": "system", "content": system_context})

    for msg in chat_history:
        role = msg.get("role")
        if role in ("assistant", "model"):
            item = {
                "role": "assistant",
                "content": msg.get("content", "") or None,
            }
            if "tool_calls" in msg and msg["tool_calls"]:
                api_tool_calls = []
                for tc in msg["tool_calls"]:
                    func = tc.get("function", {})
                    args = func.get("arguments", {})
                    args_str = json.dumps(args) if isinstance(args, dict) else str(args)
                    api_tool_calls.append(
                        {
                            "id": tc.get("id") or f"call_{func.get('name', 'dummy')}_{int(time.time())}",
                            "type": "function",
                            "function": {
                                "name": func.get("name", ""),
                                "arguments": args_str,
                            },
                        }
                    )
                item["tool_calls"] = api_tool_calls
            messages.append(item)
        elif role == "system":
            messages.append({"role": "system", "content": msg.get("content", "")})
        elif role == "tool":
            tool_call_id = "call_dummy"
            for prev in reversed(messages):
                if prev.get("role") == "assistant" and "tool_calls" in prev and prev["tool_calls"]:
                    tool_call_id = prev["tool_calls"][0].get("id", "call_dummy")
                    break
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": msg.get("content", ""),
                }
            )
        else:
            content = msg.get("content", "")
            if "images" in msg and msg["images"]:
                api_content = [{"type": "text", "text": content}]
                for img_b64 in msg["images"]:
                    api_content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                        }
                    )
                messages.append({"role": "user", "content": api_content})
            else:
                messages.append({"role": "user", "content": content})

    payload = {
        "model": "enchan-llama",
        "messages": messages,
        "stream": True,
        "timings_per_token": True,
        "temperature": float(generation_config.get("temperature", 1.0)),
        "top_p": float(generation_config.get("top_p", 0.95)),
        "top_k": int(generation_config.get("top_k", 20)),
        "presence_penalty": float(generation_config.get("presence_penalty", 1.5)),
        "max_tokens": int(generation_config.get("max_new_tokens", -1)),
        "tools": get_agent_tools_schema(),
    }

    chat_template_kwargs = {}
    if not generation_config.get("enable_thinking", True):
        chat_template_kwargs["enable_thinking"] = False
    if generation_config.get("preserve_thinking", False):
        chat_template_kwargs["preserve_thinking"] = True
    if chat_template_kwargs:
        payload["chat_template_kwargs"] = chat_template_kwargs

    if stream_output and not generation_config.get("suppress_response_header", False):
        width = shutil.get_terminal_size().columns
        print("\n\x1b[90m" + "-" * width + "\x1b[0m")

    renderer = None
    if stream_output:
        model_id = str(generation_config.get("model_id") or "llama")
        if model_id.startswith("enchan:"):
            model_id = model_id[len("enchan:"):]
        if model_id.endswith(".gguf") or "\\" in model_id or "/" in model_id:
            model_id = Path(model_id).stem
            
        from backend.ui.stream_renderer import RichStreamRenderer
        renderer = RichStreamRenderer(title=f"Enchan:{model_id}")
        renderer.start()

    start_time = time.perf_counter()
    content_parts = []
    thinking_parts = []
    tool_calls_merged = []
    think_opt = bool(generation_config.get("think", False))
    view_think = bool(generation_config.get("view_think", think_opt))
    thinking_started = False
    cancelled = False
    final_timings = {}

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    guard = GenerationInputGuard(enabled=stream_output)
    guard.start()
    try:
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                for raw_line in resp:
                    if esc_pressed():
                        cancelled = True
                        break

                    raw_line = raw_line.strip()
                    if not raw_line or not raw_line.startswith(b"data: "):
                        continue

                    data_bytes = raw_line[6:]
                    if data_bytes == b"[DONE]":
                        break

                    try:
                        chunk = json.loads(data_bytes.decode("utf-8"))
                        timings = chunk.get("timings")
                        if isinstance(timings, dict):
                            final_timings = timings
                        delta = chunk["choices"][0].get("delta", {})
                        reasoning = delta.get("reasoning_content", "")
                        content = delta.get("content", "")

                        tool_calls_chunk = delta.get("tool_calls")
                        if tool_calls_chunk:
                            for tc in tool_calls_chunk:
                                idx = tc.get("index", 0)
                                while len(tool_calls_merged) <= idx:
                                    tool_calls_merged.append(
                                        {
                                            "id": "",
                                            "type": "function",
                                            "function": {"name": "", "arguments": ""},
                                        }
                                    )

                                if "id" in tc and tc["id"]:
                                    tool_calls_merged[idx]["id"] += tc["id"]

                                func_chunk = tc.get("function", {})
                                if "name" in func_chunk and func_chunk["name"]:
                                    tool_calls_merged[idx]["function"]["name"] += func_chunk["name"]

                                if "arguments" in func_chunk and func_chunk["arguments"]:
                                    tool_calls_merged[idx]["function"]["arguments"] += func_chunk["arguments"]

                        if reasoning:
                            thinking_parts.append(reasoning)
                            if stream_output and renderer is not None:
                                if view_think:
                                    renderer.update_thinking(reasoning)

                        if content:
                            content_parts.append(content)
                            if stream_output and renderer is not None:
                                renderer.update_content(content)
                            if chunk_callback is not None:
                                chunk_callback(content)
                    except Exception:
                        pass

                    if esc_pressed():
                        cancelled = True
                        break
        except urllib.error.HTTPError as e:
            if renderer is not None:
                renderer.finish()
            body = e.read().decode("utf-8", errors="replace")
            print(f"\n[Error] Enchan Llama HTTP error {e.code}: {body}")
            return None
        except Exception as e:
            if renderer is not None:
                renderer.finish()
            print(f"\n[Error] Enchan Llama request failed: {e}")
            return None
    finally:
        if renderer is not None:
            renderer.finish()
        guard.stop()

    elapsed = time.perf_counter() - start_time
    response = "".join(content_parts)
    thinking = "".join(thinking_parts)
    if response:
        clean_response, fallback_thinking = split_thought_blocks(response)
        if fallback_thinking and not thinking:
            thinking = fallback_thinking
        response = clean_response

    parsed_tool_calls = []
    for tc in tool_calls_merged:
        name = tc["function"]["name"]
        raw_args = tc["function"]["arguments"]
        tc_id = tc.get("id") or f"call_{name}_{int(time.time())}"
        try:
            args = json.loads(raw_args) if raw_args else {}
        except Exception:
            args = {}
        parsed_tool_calls.append(
            {
                "id": tc_id,
                "type": "function",
                "function": {"name": name, "arguments": args},
            }
        )

    if cancelled:
        if stream_output:
            print("\n\x1b[2;90m[System] Enchan Llama generation cancelled by Esc.\x1b[0m")
        return {
            "cancelled": True,
            "response": response,
            "thinking": thinking,
            "tool_calls": parsed_tool_calls,
            "elapsed_sec": elapsed,
        }

    if stream_output:
        print()

    predicted_n = int(final_timings.get("predicted_n") or 0) if final_timings else 0
    predicted_tps = float(final_timings.get("predicted_per_second") or 0.0) if final_timings else 0.0
    prompt_n = int(final_timings.get("prompt_n") or 0) if final_timings else 0
    prompt_tps = float(final_timings.get("prompt_per_second") or 0.0) if final_timings else 0.0
    fallback_tokens_count = len(response) // 4
    tps = predicted_tps if predicted_tps > 0 else (fallback_tokens_count / elapsed if elapsed > 0 else 0)
    if show_metrics and stream_output:
        if predicted_tps > 0:
            print(
                "\x1b[90m"
                f"[Metrics] llama.cpp eval: {predicted_n} tok @ {predicted_tps:.1f} t/s"
                f" | prompt: {prompt_n} tok @ {prompt_tps:.1f} t/s"
                f" | wall: {elapsed:.1f}s"
                "\x1b[0m"
            )
        else:
            print(
                f"\x1b[90m[Metrics] wall fallback: ~{fallback_tokens_count} chars/4 tok "
                f"in {elapsed:.1f}s ({tps:.1f} t/s)\x1b[0m"
            )

    return {
        "cancelled": False,
        "response": response,
        "thinking": thinking,
        "tool_calls": parsed_tool_calls,
        "elapsed_sec": elapsed,
        "tps": tps,
        "tokens_count": predicted_n or fallback_tokens_count,
        "timings": final_timings,
        "metrics_source": "llama.cpp" if predicted_tps > 0 else "wall_fallback",
    }


def run_enchan_llama_once(
    prompt: str,
    chat_history: list[dict],
    generation_config: dict,
    session_log_path: Path,
    args,
    tokenizer=None,
    plain: bool = False,
    memory_context: str = "",
) -> None:
    from backend.agent_loop import run_agent_loop
    from backend.ollama_backend import build_agent_goal_prompt, count_text_tokens, estimate_text_tokens_rough, format_count
    from backend.session_log import append_session_event

    if not enchan_base.ensure_enchan_llama_for_request(generation_config, args):
        append_session_event(session_log_path, {"type": "error", "stage": "enchan_llama_start"})
        return

    current_prompt = build_agent_goal_prompt(prompt, memory_context)
    chat_history.append({"role": "user", "content": current_prompt})
    input_length = count_text_tokens(tokenizer, current_prompt) if tokenizer is not None else estimate_text_tokens_rough(current_prompt)
    max_input_tokens = int(generation_config["max_input_tokens"])
    if input_length > max_input_tokens:
        chat_history.pop()
        print(f"[Error] Prompt is {format_count(input_length)} tokens, which exceeds limit.")
        return

    append_session_event(
        session_log_path,
        {
            "type": "message",
            "role": "user",
            "display_input": prompt,
            "content": current_prompt,
            "input_tokens_estimate": input_length,
            "backend": "enchan",
            "single_turn": True,
        },
    )

    host = f"http://localhost:{enchan_base.DEFAULT_ENCHAN_LLAMA_PORT}"
    run_agent_loop(
        chat_history=chat_history,
        generation_config=generation_config,
        session_log_path=session_log_path,
        backend="enchan",
        generate_response=lambda: generate_enchan_llama_response(
            chat_history,
            generation_config,
            session_log_path,
            host=host,
            stream_output=not plain,
            show_metrics=not plain,
        ),
        append_tool_result_event=enchan_base.append_tool_result_event,
        tokenizer=tokenizer,
        plain=plain,
        single_turn=True,
        strip_final_thoughts=False,
        print_plain_final=True,
    )


def run_enchan_llama_agent_turn(
    chat_history: list[dict],
    generation_config: dict,
    session_log_path: Path,
    args,
    tokenizer=None,
) -> None:
    from backend.agent_loop import run_agent_loop
    from backend.session_log import append_session_event

    host = f"http://localhost:{enchan_base.DEFAULT_ENCHAN_LLAMA_PORT}"
    if not enchan_base.ensure_enchan_llama_for_request(generation_config, args):
        append_session_event(session_log_path, {"type": "error", "stage": "enchan_llama_start"})
        return

    run_agent_loop(
        chat_history=chat_history,
        generation_config=generation_config,
        session_log_path=session_log_path,
        backend="enchan",
        generate_response=lambda: generate_enchan_llama_response(
            chat_history,
            generation_config,
            session_log_path,
            host=host,
            stream_output=True,
            show_metrics=True,
        ),
        append_tool_result_event=enchan_base.append_tool_result_event,
        tokenizer=tokenizer,
        print_before_action_newline=True,
    )


def run_ollama_once(*args, **kwargs):
    with GenerationInputGuard(enabled=not kwargs.get("plain", False)):
        return ollama_base.run_ollama_once(*args, **kwargs)


def run_ollama_agent_turn(*args, **kwargs):
    with GenerationInputGuard(enabled=True):
        return ollama_base.run_ollama_agent_turn(*args, **kwargs)
