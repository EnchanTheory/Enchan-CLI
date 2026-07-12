import copy
from typing import Any

AGENT_TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Primary local code search. Prefer rg when available. Returns paths, line numbers, and compact context. Supports mode='compress' to summarize/group large search results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query or regex pattern"},
                    "regex": {"type": "boolean", "description": "Treat query as a regular expression. False uses fixed-string search where possible."},
                    "path": {"type": "string", "description": "File or directory to search from (optional, default workspace)"},
                    "context_lines": {"type": "integer", "description": "Context lines around each match (optional, default 2, max 5)"},
                    "max_results": {"type": "integer", "description": "Maximum results to return (optional, default 80, max 200)"},
                    "mode": {"type": "string", "description": "Set to 'compress' to summarize/group large search results (optional)"},
                    "compress_query": {"type": "string", "description": "Specific extraction query when mode='compress' (optional)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Primary file reader. Use line ranges for precise code work; use mode='compress' for large documents or structured extraction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path to the file"},
                    "lines": {"type": "string", "description": "Specific lines to read (e.g. '1-50', '50-100') (optional)"},
                    "mode": {"type": "string", "description": "Set to 'compress' for summarization/extraction mode (optional)"},
                    "query": {"type": "string", "description": "Specific query to extract when using 'compress' mode (optional)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Single local file editing tool. Supports unified diff patches, exact old/new replacement, and explicit write/create. Use apply=false for dry runs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Target file path for replace/write operations"},
                    "patch": {"type": "string", "description": "Unified diff patch string for patch edits"},
                    "old": {"type": "string", "description": "Exact existing text to replace; must match exactly once"},
                    "new": {"type": "string", "description": "Replacement text for exact replace"},
                    "content": {"type": "string", "description": "Complete file content for create/write mode"},
                    "overwrite": {"type": "boolean", "description": "Allow replacing an existing file in content/write mode"},
                    "apply": {"type": "boolean", "description": "Set false for a dry run; true/default applies the edit"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "General terminal command execution surface. Use for git, directory listing, tests, builds, diagnostics, scripts, and fallback actions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The exact command to execute"},
                    "cwd": {"type": "string", "description": "Working directory for the command (optional)"},
                    "shell": {"type": "string", "description": "Shell to use: powershell, cmd, sh, or bash (optional)"},
                    "timeout_seconds": {"type": "integer", "description": "Timeout in seconds (optional, default 30)"},
                    "max_output_chars": {"type": "integer", "description": "Maximum characters to capture from output (optional)"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_browse",
            "description": "Primary web research tool. For a query, it discovers relevant pages, opens the actual sites, filters weak or duplicate results, and returns readable page content. Use it for current facts, documentation, products, news, comparisons, and any question requiring web evidence. Search-result titles and snippets are discovery hints only; base the answer on opened page contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "HTTP(S) URL to open directly (optional if query is provided)"},
                    "query": {"type": "string", "description": "Research query. The tool will search and open relevant sites automatically (optional if url is provided)"},
                    "max_pages": {"type": "integer", "description": "Maximum readable pages to return for a query (optional, default 3)"},
                    "max_chars_per_page": {"type": "integer", "description": "Maximum readable text characters per opened page (optional, default 12000)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "Lists the full registered skill catalog, including method schemas. Keep this because skills are a unique capability.",
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
            "description": "Runs an installed skill as a first-class capability. Installed skill names and summaries are injected dynamically at runtime; when a task matches one, call this before generic tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Name of the skill to run"},
                    "argument": {"type": "string", "description": "Legacy one-shot argument string (optional)"},
                    "method": {"type": "string", "description": "Specific method to invoke (optional)"},
                    "params": {"type": "object", "description": "Arguments for the typed method (optional)"}
                },
                "required": ["skill_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_agent",
            "description": "Delegates a complex prompt or task to an external agent model (e.g. codex, gemini, claude). Keep this because external delegation is a unique capability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent": {"type": "string", "description": "Target agent name ('codex', 'gemini', or 'claude')"},
                    "prompt": {"type": "string", "description": "The prompt or task context to delegate"}
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
