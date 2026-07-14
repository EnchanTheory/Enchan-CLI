import copy
from typing import Any

AGENT_TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search local code and return paths, line numbers, and compact context. Use mode='compress' for large results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text or regex to search"},
                    "regex": {"type": "boolean", "description": "Interpret query as regex; false uses fixed text"},
                    "path": {"type": "string", "description": "Search root; default workspace"},
                    "context_lines": {"type": "integer", "description": "Lines around matches; default 2, max 5"},
                    "max_results": {"type": "integer", "description": "Result limit; default 80, max 200"},
                    "mode": {"type": "string", "description": "Use 'compress' to group/summarize results"},
                    "compress_query": {"type": "string", "description": "Extraction query for compress mode"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a local file. Use line ranges for precision or mode='compress' for large documents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "lines": {"type": "string", "description": "Line range, e.g. '1-50'"},
                    "mode": {"type": "string", "description": "Use 'compress' for summary/extraction"},
                    "query": {"type": "string", "description": "Extraction query for compress mode"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit one local file by patch, exact replacement, or full write. Set apply=false for a dry run.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Target file path"},
                    "patch": {"type": "string", "description": "Unified diff patch"},
                    "old": {"type": "string", "description": "Exact text to replace once"},
                    "new": {"type": "string", "description": "Replacement text"},
                    "content": {"type": "string", "description": "Full content for create/write"},
                    "overwrite": {"type": "boolean", "description": "Allow overwrite in write mode"},
                    "apply": {"type": "boolean", "description": "False=dry run; default true"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run terminal commands for git, tests, builds, diagnostics, scripts, and fallback actions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Exact command"},
                    "cwd": {"type": "string", "description": "Working directory"},
                    "shell": {"type": "string", "description": "powershell, cmd, sh, or bash"},
                    "timeout_seconds": {"type": "integer", "description": "Timeout; default 30 seconds"},
                    "max_output_chars": {"type": "integer", "description": "Output character limit"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_browse",
            "description": "Search and open web pages for current evidence. Base answers on opened page content, not result snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "HTTP(S) URL; optional when query is set"},
                    "query": {"type": "string", "description": "Query to search and open relevant pages"},
                    "max_pages": {"type": "integer", "description": "Page limit; default 3"},
                    "max_chars_per_page": {"type": "integer", "description": "Characters per page; default 12000"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "List registered skills and method schemas.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "use_skill",
            "description": "Run an installed skill. Runtime injects current skill names and summaries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Installed skill name"},
                    "argument": {"type": "string", "description": "Legacy one-shot argument"},
                    "method": {"type": "string", "description": "Method to invoke"},
                    "params": {"type": "object", "description": "Typed method arguments"}
                },
                "required": ["skill_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_agent",
            "description": "Delegate a complex prompt or task to an external agent model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent": {"type": "string", "description": "codex, gemini, or claude"},
                    "prompt": {"type": "string", "description": "Prompt or task context"}
                },
                "required": ["agent", "prompt"]
            }
        }
    }
]


def get_agent_tools_schema() -> list[dict[str, Any]]:
    """Return the tool schema with the live skill registry embedded in skill tools."""
    schema = copy.deepcopy(AGENT_TOOLS_SCHEMA)
    try:
        from backend.skills_loader import get_registered_skill_names, render_skill_tool_hint
        skill_names = get_registered_skill_names()
        skill_hint = render_skill_tool_hint()
    except Exception as e:
        skill_names = []
        skill_hint = f"Skill registry unavailable: {e}"

    for tool in schema:
        function = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if name == "list_skills":
            function["description"] = (
                "Lists the full registered skill catalog, including method schemas. "
                "Do not use this for initial discovery; installed skills are already auto-surfaced. "
                f"Current installed skills: {skill_hint}"
            )
        elif name == "use_skill":
            function["description"] = (
                "Runs an installed skill as a first-class capability. "
                "If the user task matches any installed skill below, call use_skill before generic tools. "
                f"Current installed skills: {skill_hint}"
            )
            params = function.get("parameters")
            if isinstance(params, dict):
                props = params.get("properties")
                if isinstance(props, dict):
                    skill_name_prop = props.get("skill_name")
                    if isinstance(skill_name_prop, dict):
                        skill_name_prop["description"] = "Installed skill name. Choose from the live auto-registered skill catalog."
                        if skill_names:
                            skill_name_prop["enum"] = skill_names
    return schema
