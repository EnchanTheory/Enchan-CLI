from pathlib import Path
from backend.thinking import strip_thought_blocks
import sys
from typing import Callable

BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent

from backend.agent_tools import (
    AGENT_MAX_ITERATIONS,
    execute_agent_tool,
    truncate_observation,
    get_max_obs_chars,
)
from backend.session_log import append_session_event
from backend.ui_theme import get_spinner_status, print_agent_action, print_agent_observation


SENSITIVE_SPINNER_TOOLS = {
    "edit_file",
    "use_skill",
    "run_command",
    "delegate_agent",
}


def _is_compress_call(call: dict) -> bool:
    return (
        call.get("tool") in {"read_file", "search_code"}
        and str(call.get("args", {}).get("mode", "")).lower() == "compress"
    )


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
        "content": strip_thought_blocks(response_text),
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
    spinner_text = "Compressing..." if _is_compress_call(call) else f"Calling {tool_name}..."
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
    tool_executor: Callable[[dict, object], dict] | None = None,
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
    try:
        from backend.approval import approval_scope

        with approval_scope(session_log_path=session_log_path):
            result = (tool_executor(call, tokenizer) if tool_executor else execute_agent_tool(call, tokenizer=tokenizer))
    except Exception as e:
        result = {
            "tool": call.get("tool"),
            "ok": False,
            "observation": f"Tool raised an exception: {e}",
        }
    finally:
        if status is not None and hasattr(status, "stop"):
            status.stop()

    observation = truncate_observation(
        result["observation"],
        max_chars=int(result.get("observation_max_chars") or get_max_obs_chars()),
    )
    hide_observation = _is_compress_call(call)
    visible_observation = (
        "[Internal compressed context hidden from display and session log; delivered to the agent for analysis.]"
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
    observation_text = f"Observation: [{result['tool']}] ok={result['ok']}\n{observation}"
    if not result["ok"]:
        observation_text += (
            "\nIMPORTANT: This tool action failed. Do not claim that it succeeded. "
            "Retry with corrected arguments when possible; otherwise report the failure clearly."
        )
    return observation_text


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
    tool_executor: Callable[[dict, object], dict] | None = None,
) -> None:
    for iteration in range(1, AGENT_MAX_ITERATIONS + 1):
        generation = generate_response()
        if generation is None or generation.get("cancelled"):
            return

        response_text = generation["response"]
        tool_calls = generation.get("tool_calls")

        if not tool_calls:
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
                if generation_config.get("view_think", False):
                    print(response_text)
                else:
                    print(strip_thought_blocks(response_text))
            return

        # Append the assistant message including every requested tool call before results.
        assistant_msg = {"role": "assistant", "content": strip_thought_blocks(response_text), "tool_calls": tool_calls}
        if generation.get("thinking"):
            assistant_msg["thinking"] = generation["thinking"]
        chat_history.append(assistant_msg)

        # Execute every returned tool call sequentially. One tool result is appended per tool_call id.
        for index, tc in enumerate(tool_calls):
            call = {
                "tool": tc.get("function", {}).get("name", ""),
                "args": tc.get("function", {}).get("arguments", {})
            }

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
                tool_executor=tool_executor,
            )

            if index == len(tool_calls) - 1:
                observation_text += "\nContinue."

            tool_msg = {"role": "tool", "content": observation_text}
            if tc.get("id"):
                tool_msg["tool_call_id"] = tc.get("id")
            chat_history.append(tool_msg)

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