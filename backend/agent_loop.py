from pathlib import Path
import re
import sys
from typing import Callable

BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent

from agent_tools import (
    AGENT_MAX_ITERATIONS,
    execute_agent_tool,
    parse_agent_tool_call,
    truncate_observation,
)
from session_log import append_session_event
from ui_theme import get_spinner_status, print_agent_action, print_agent_observation


SENSITIVE_SPINNER_TOOLS = {
    "write_text_file",
    "apply_patch",
    "host_shell",
    "execute_command",
    "use_skill",
    "delegate_agent",
    "replace_text",
    "git_add",
    "git_commit",
}


def strip_thought_blocks(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


def _assistant_message_from_generation(response_text: str, generation: dict, *, strip_thoughts: bool) -> dict:
    content = strip_thought_blocks(response_text) if strip_thoughts else response_text
    assistant_message = {"role": "assistant", "content": content}
    if generation.get("thinking"):
        assistant_message["thinking"] = generation["thinking"]
    return assistant_message


def _assistant_event(
    response_text: str,
    generation: dict,
    *,
    backend: str,
    single_turn: bool,
) -> dict:
    event = {
        "type": "message",
        "role": "assistant",
        "content": response_text,
        "backend": backend,
    }
    if single_turn:
        event["single_turn"] = True
    if generation.get("thinking"):
        event["thinking"] = generation.get("thinking", "")
    for key in ("output_tokens", "tokens_count", "tps", "metrics_source", "timings"):
        if key in generation:
            event[key] = generation.get(key)
    return event


def _tool_spinner(call: dict):
    tool_name = call.get("tool")
    if tool_name in SENSITIVE_SPINNER_TOOLS:
        return None
    spinner_text = (
        "Compressing..."
        if tool_name == "read_document"
        and str(call.get("args", {}).get("mode", "")).lower() == "compress"
        else f"Calling {tool_name}... (esc to cancel)"
    )
    status = get_spinner_status(spinner_text)
    if hasattr(status, "start"):
        status.start()
    return status


def _run_tool_observation(
    call: dict,
    *,
    tokenizer,
    backend: str,
    iteration: int,
    session_log_path: Path,
    single_turn: bool,
    plain: bool,
    print_before_action_newline: bool,
    append_tool_result_event: Callable[[Path, dict, int, str], None],
) -> str:
    if not plain:
        if print_before_action_newline:
            print()
        print_agent_action(call.get("tool"), call.get("args", {}))
    event = {
        "type": "agent_action",
        "iteration": iteration,
        "tool": call.get("tool"),
        "args": call.get("args", {}),
        "backend": backend,
    }
    if single_turn:
        event["single_turn"] = True
    append_session_event(session_log_path, event)

    status = _tool_spinner(call)
    result = execute_agent_tool(call, tokenizer=tokenizer)
    if status is not None and hasattr(status, "stop"):
        status.stop()

    observation = truncate_observation(
        result["observation"],
        max_chars=int(result.get("observation_max_chars", 6000)),
    )
    hide_observation = (
        call.get("tool") == "read_document"
        and str(call.get("args", {}).get("mode", "")).lower() == "compress"
    )
    visible_observation = (
        "[Internal compressed document context hidden from display and session log; delivered to the agent for analysis.]"
        if hide_observation
        else observation
    )
    if not plain and not result.get("displayed"):
        print_agent_observation(result["tool"], result["ok"], visible_observation)
    elif hide_observation:
        print(f"Observation: [{result['tool']}] ok={result['ok']}\n{visible_observation}")

    observation_event = {
        "type": "tool_observation",
        "iteration": iteration,
        "tool": result["tool"],
        "ok": result["ok"],
        "observation": visible_observation,
        "observation_hidden": hide_observation,
        "backend": backend,
    }
    if single_turn:
        observation_event["single_turn"] = True
    append_session_event(session_log_path, observation_event)
    append_tool_result_event(session_log_path, result, iteration, backend)
    return f"Observation: [{result['tool']}] ok={result['ok']}\n{observation}"


def run_agent_loop(
    *,
    chat_history: list[dict],
    generation_config: dict,
    session_log_path: Path,
    backend: str,
    generate_response: Callable[[], dict | None],
    append_tool_result_event: Callable[[Path, dict, int, str], None],
    tokenizer=None,
    plain: bool = False,
    single_turn: bool = False,
    strip_final_thoughts: bool = True,
    print_plain_final: bool = False,
    print_before_action_newline: bool = False,
) -> None:
    for iteration in range(1, AGENT_MAX_ITERATIONS + 1):
        generation = generate_response()
        if generation is None or generation.get("cancelled"):
            return

        response_text = generation["response"]
        call = parse_agent_tool_call(response_text)
        if call is None:
            chat_history.append(
                _assistant_message_from_generation(
                    response_text,
                    generation,
                    strip_thoughts=strip_final_thoughts,
                )
            )
            append_session_event(
                session_log_path,
                _assistant_event(
                    response_text,
                    generation,
                    backend=backend,
                    single_turn=single_turn,
                ),
            )
            if plain and print_plain_final:
                print(response_text)
            return

        observation_text = _run_tool_observation(
            call,
            tokenizer=tokenizer,
            backend=backend,
            iteration=iteration,
            session_log_path=session_log_path,
            single_turn=single_turn,
            plain=plain,
            print_before_action_newline=print_before_action_newline,
            append_tool_result_event=append_tool_result_event,
        )
        chat_history.append({"role": "assistant", "content": strip_thought_blocks(response_text)})
        chat_history.append({"role": "user", "content": observation_text + "\nContinue."})

    append_session_event(
        session_log_path,
        {
            "type": "agent_loop_limit",
            "max_iterations": AGENT_MAX_ITERATIONS,
            "backend": backend,
            **({"single_turn": True} if single_turn else {}),
        },
    )
    if not plain:
        print(f"[Agent] Aborted after {AGENT_MAX_ITERATIONS} tool iterations.")

