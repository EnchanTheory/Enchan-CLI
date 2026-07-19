"""SNS-only agent session and tool boundary."""
import json

from backend.agent_loop import run_agent_loop as _run_base_agent_loop
from backend.session_log import append_session_event
from backend.webui.sns.agent_tools import execute_sns_tool


REQUIRED_CONTEXT_TOOLS = (
    ("sns_get_current_context", {}),
    ("sns_get_own_tweet_history", {"max_posts": 30, "token_budget": 6000}),
    ("sns_search_news", {"query": "top world news"}),
)


def run_sns_agent_loop(*, broker, chat_history, session_log_path, backend, **kwargs):
    """Run one SNS session containing Phase 2 history, context, tools, and output.

    Required observations are attached to the same chat history before the first
    model call. Any later model-requested SNS tools continue in that same history.
    """
    for iteration, (tool_name, tool_args) in enumerate(REQUIRED_CONTEXT_TOOLS, start=1):
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
        chat_history.append({
            "role": "tool",
            "tool_call_id": call_id,
            "content": (
                f"Observation: [{tool_name}] ok=True\n"
                + json.dumps(tool_result.get("observation"), ensure_ascii=False)
            ),
        })

    return _run_base_agent_loop(
        chat_history=chat_history,
        session_log_path=session_log_path,
        backend=backend,
        **kwargs,
    )
