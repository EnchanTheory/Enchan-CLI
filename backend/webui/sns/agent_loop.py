"""SNS-only agent session and tool boundary."""
import json

from backend.agent_loop import run_agent_loop as _run_base_agent_loop
from backend.session_log import append_session_event
from backend.thinking import strip_thought_blocks
from backend.webui.sns.agent_tools import execute_sns_tool


def _attach_required_tool(
    *, tool_name, tool_args, iteration, broker, chat_history,
    session_log_path, backend,
):
    append_session_event(session_log_path, {
        "type": "agent_action",
        "iteration": iteration,
        "tool": tool_name,
        "args": tool_args,
        "backend": backend,
        "sns_required": True,
    })
    tool_result = execute_sns_tool(tool_name, tool_args, broker)
    append_session_event(session_log_path, {
        "type": "tool_observation",
        "iteration": iteration,
        "tool": tool_name,
        "ok": bool(tool_result.get("ok")),
        "observation": tool_result.get("observation"),
        "observation_hidden": False,
        "backend": backend,
        "sns_required": True,
    })
    if not tool_result.get("ok"):
        raise RuntimeError(f"Required SNS tool failed: {tool_name}")

    call_id = f"sns-required-{iteration}"
    chat_history.append({
        "role": "assistant",
        "content": "",
        "tool_calls": [{
            "id": call_id,
            "type": "function",
            "function": {"name": tool_name, "arguments": tool_args},
        }],
    })
    observation_message = {
        "role": "tool",
        "tool_call_id": call_id,
        "content": (
            f"Observation: [{tool_name}] ok=True\n"
            + json.dumps(tool_result.get("observation"), ensure_ascii=False)
        ),
    }
    chat_history.append(observation_message)
    return observation_message


def _run_private_stage(
    *, system_context, generation_config, generate_response, max_new_tokens=192,
):
    original_system_context = generation_config.get("system_context")
    original_disable_tools = generation_config.get("disable_tools", False)
    original_max_new_tokens = generation_config.get("max_new_tokens", 256)
    try:
        generation_config["system_context"] = system_context
        generation_config["disable_tools"] = True
        generation_config["max_new_tokens"] = min(
            int(original_max_new_tokens), max_new_tokens,
        )
        generation = generate_response()
    finally:
        generation_config["system_context"] = original_system_context
        generation_config["disable_tools"] = original_disable_tools
        generation_config["max_new_tokens"] = original_max_new_tokens

    if not generation or generation.get("cancelled"):
        raise RuntimeError("SNS private stage was cancelled")
    content = strip_thought_blocks(str(generation.get("response") or "")).strip()
    if not content:
        raise RuntimeError("The model returned no SNS private-stage result")
    return content


def run_sns_agent_loop(
    *, broker, chat_history, session_log_path, backend, system_locale="en-US",
    selection_system_context, generation_config, generate_response, **kwargs,
):
    """Run current-topic selection and writing without loading past posts."""
    trends_observation = _attach_required_tool(
        tool_name="sns_get_regional_trends",
        tool_args={"locale": system_locale},
        iteration=1,
        broker=broker,
        chat_history=chat_history,
        session_log_path=session_log_path,
        backend=backend,
    )
    selection = _run_private_stage(
        system_context=selection_system_context,
        generation_config=generation_config,
        generate_response=generate_response,
    )
    append_session_event(session_log_path, {
        "type": "sns_topic_selection",
        "content": selection,
        "backend": backend,
    })
    # The writing call receives only the chosen topic, not every competing headline.
    trends_observation["content"] = (
        "Observation: [sns_get_regional_trends] ok=True\n"
        "The full trend list was reviewed and removed from working context. "
        "Use the internal topic selection instead."
    )
    chat_history.append({
        "role": "assistant",
        "content": f"[INTERNAL TOPIC SELECTION]\n{selection}",
    })

    _attach_required_tool(
        tool_name="sns_get_current_context",
        tool_args={},
        iteration=2,
        broker=broker,
        chat_history=chat_history,
        session_log_path=session_log_path,
        backend=backend,
    )
    chat_history.append({
        "role": "user",
        "content": (
            "Use the internal topic selection above. Now write only the final "
            "SNS post, following the system instructions."
        ),
    })

    return _run_base_agent_loop(
        chat_history=chat_history,
        session_log_path=session_log_path,
        backend=backend,
        generation_config=generation_config,
        generate_response=generate_response,
        **kwargs,
    )
