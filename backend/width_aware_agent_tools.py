"""Agent tool registry with width-aware streaming skill output.

This module keeps the existing agent tool implementations intact and replaces
only the `use_skill` tool entry so streaming skill observations use the same
width-aware manual frame renderer as the visible agent loop.
"""

from __future__ import annotations

import json
import shutil
import subprocess

from backend import agent_tools as base

AGENT_MAX_ITERATIONS = base.AGENT_MAX_ITERATIONS
get_max_obs_chars = base.get_max_obs_chars
truncate_observation = base.truncate_observation


def tool_use_skill(args: dict) -> dict:
    skill_name = args.get("skill_name") or args.get("name")
    argument = args.get("argument") or args.get("value") or ""
    method = args.get("method")
    params = args.get("params") if isinstance(args.get("params"), dict) else None
    if not skill_name:
        return {"ok": False, "error": "use_skill requires 'skill_name'."}
    if params is None and not argument:
        params = {}

    from contextlib import redirect_stderr, redirect_stdout
    from backend.manual_frames import stream_agent_observation
    from backend.skills_loader import SkillError, run_skill

    stream = stream_agent_observation("use_skill")
    ok = True
    content = ""
    try:
        with redirect_stdout(stream), redirect_stderr(stream):
            content = run_skill(str(skill_name), str(argument), method=str(method) if method else None, params=params)
        returned = str(content or "").strip()
        if returned and returned not in stream.getvalue():
            stream.write(("\n" if stream.getvalue().strip() else "") + returned + "\n")
    except SkillError as e:
        ok = False
        content = str(e)
        if content:
            stream.write(("\n" if stream.getvalue().strip() else "") + content + "\n")
    except Exception as e:
        ok = False
        content = f"Internal error while running skill '{skill_name}': {e}"
        stream.write(content + "\n")
    finally:
        stream.close()

    captured = stream.getvalue().strip()
    if captured:
        content = captured
    return {"ok": ok, "content": content, "displayed": True}


TOOL_REGISTRY = dict(base.TOOL_REGISTRY)
TOOL_REGISTRY["use_skill"] = tool_use_skill


def _tool_requires_permission(tool_name: str, args: dict) -> bool:
    return base._tool_requires_permission(tool_name, args)


def _interactive_security_prompt() -> bool:
    return base._interactive_security_prompt()


def execute_agent_tool(call: dict, tokenizer=None, model=None) -> dict:
    tool_name = call.get("tool")
    if tool_name == "_parse_error":
        return {"tool": tool_name, "ok": False, "observation": call.get("error", "Invalid tool call.")}

    tool = TOOL_REGISTRY.get(tool_name)
    if tool is None:
        available = ", ".join(sorted(TOOL_REGISTRY))
        return {"tool": tool_name, "ok": False, "observation": f"Unknown tool: {tool_name}. Available tools: {available}"}

    args = dict(call.get("args", {}))
    if _tool_requires_permission(tool_name, args):
        print(f"\n\x1b[38;2;190;170;120m⚠️  [Security Request]\x1b[0m \x1b[38;2;210;200;200mThe local Enchan AI wants to perform a sensitive action:\x1b[0m")
        print(f"  \x1b[38;2;210;200;200mTool: {tool_name}\x1b[0m")
        if tool_name == "edit_file":
            print(f"  \x1b[38;2;210;200;200mTarget: {args.get('path') or '[patch]'}\x1b[0m")
        elif tool_name == "use_skill":
            print(f"  \x1b[38;2;210;200;200mSkill: {args.get('skill_name') or args.get('name') or 'unknown'}\x1b[0m")
        if not _interactive_security_prompt():
            print("\x1b[38;2;180;100;100m  [System] Execution denied by user.\x1b[0m")
            return {"tool": tool_name, "ok": False, "observation": "User denied permission to execute this tool."}

    if tokenizer is not None:
        args["__tokenizer"] = tokenizer
    if model is not None:
        args["__model"] = model

    result = tool(args)
    observation = result.get("content") or result.get("error")
    response = {"tool": tool_name, "ok": bool(result.get("ok")), "observation": observation or ""}
    if isinstance(result.get("observation_max_chars"), int):
        response["observation_max_chars"] = result["observation_max_chars"]
    if isinstance(result.get("event"), dict):
        response["event"] = result["event"]
    if result.get("displayed"):
        response["displayed"] = True
    return response
