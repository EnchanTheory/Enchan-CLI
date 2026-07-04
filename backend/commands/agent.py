from pathlib import Path
from backend.core import registry
from session_log import append_session_event

@registry.command("/delegate", desc="Delegate a task prompt to a subagent.", usage="/delegate <codex|gemini|claude> <task prompt>")
def handle_delegate(
    user_input: str,
    session_log_path: Path | None = None,
    **kwargs
) -> tuple[bool, str, bool]:
    """Delegates a prompt to a named agent (e.g., codex, gemini) and registers the observation."""
    file_context = kwargs.get("file_context", "")
    delegate_parts = user_input.strip().split(maxsplit=2)
    
    if len(delegate_parts) < 3:
        print("[Error] Usage: /delegate <codex|gemini|claude> <task prompt>")
        return True, file_context, False
        
    agent_name = delegate_parts[1].lower()
    prompt = delegate_parts[2]
    
    try:
        # Dynamic/Lazy import of heavy agent_tools to keep general CLI startup instant!
        from agent_tools import execute_agent_tool
        result = execute_agent_tool({"tool": "delegate_agent", "args": {"agent": agent_name, "prompt": prompt}})
    except Exception as e:
        print(f"[Error] Delegation failed: {e}")
        return True, file_context, False
        
    observation = result.get("observation", "")
    ok = result.get("ok", False)
    print(f"\n[Delegate:{agent_name}] {'OK' if ok else 'FAILED'}")
    
    if observation:
        print(observation)
        
    append_session_event(
        session_log_path,
        {"type": "delegate_agent", "agent": agent_name, "ok": ok, "observation": observation[:4000]},
    )
    
    return True, file_context, False
