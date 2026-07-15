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
                    "regex": {"type": "boolean", "description": "Treat query as regex; false uses fixed-string search where possible"},
                    "path": {"type": "string", "description": "File or directory to search; default workspace"},
                    "context_lines": {"type": "integer", "description": "Context lines around each match; default 2, max 5"},
                    "max_results": {"type": "integer", "description": "Requested match limit; default 80, max 200"},
                    "mode": {"type": "string", "description": "Use 'compress' to summarize/group large results"},
                    "compress_query": {"type": "string", "description": "Specific extraction query for compress mode"}
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
            "description": "Single local file editing tool. Choose exactly one operation: patch alone; exact replacement with old plus new (content is accepted as an alias for new); or write/create with content. Do not combine patch with replacement/write fields. Use apply=false for dry runs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Target file path for replace/write operations"},
                    "patch": {"type": "string", "description": "Unified diff patch"},
                    "old": {"type": "string", "description": "Exact existing text; must match once"},
                    "new": {"type": "string", "description": "Replacement text for exact replace; use an empty string to delete the matched text"},
                    "content": {"type": "string", "description": "Complete content for create/write mode; also accepted as replacement text when old is supplied"},
                    "overwrite": {"type": "boolean", "description": "Allow replacing an existing file in write mode"},
                    "apply": {"type": "boolean", "description": "False for dry run; true/default applies the edit"}
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
                    "timeout_seconds": {"type": "integer", "description": "Timeout in seconds (optional, default 30, max 300)"},
                    "max_output_chars": {"type": "integer", "description": "Maximum captured output characters; default configured observation limit, max 500000"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_rag",
            "description": "Search all registered local RAG collections and return MaxCut-selected evidence with source metadata. Use it whenever the request may depend on indexed documents or earlier conversations, and cite the returned sources.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural-language retrieval query"},
                    "collection": {"type": "string", "description": "Collection ID or name (optional, default: all registered sources)"},
                    "limit": {"type": "integer", "description": "Maximum selected chunks (optional, default 6, max 20)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_browse",
            "description": "Searches for relevant pages or opens a URL, then returns readable page content. Use opened page content as evidence; titles and snippets are discovery hints only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "HTTP(S) URL to open directly (optional if query is provided)"},
                    "query": {"type": "string", "description": "Research query. The tool searches and opens relevant pages automatically (optional if url is provided)"},
                    "max_pages": {"type": "integer", "description": "Maximum readable pages for a query; default 3, max 5"},
                    "max_chars_per_page": {"type": "integer", "description": "Maximum readable characters per page; default 12000, range 2000-30000"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "use_skill",
            "description": "Runs an installed skill as a first-class capability. Installed skill names, methods, and input schemas are auto-loaded into the system prompt; when a task matches one, call this before generic tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Name of the installed skill to run"},
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
            "description": "Delegates a complex prompt or task to an installed external agent command: codex, gemini, or claude.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent": {"type": "string", "description": "Target agent: codex, gemini, or claude"},
                    "prompt": {"type": "string", "description": "The prompt or task context to delegate"}
                },
                "required": ["agent", "prompt"]
            }
        }
    }
]


def get_agent_tools_schema() -> list[dict[str, Any]]:
    """Return the tool schema with the live skill registry embedded in use_skill."""
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
        if not isinstance(function, dict) or function.get("name") != "use_skill":
            continue
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
                    skill_name_prop["description"] = "Installed skill name from the auto-loaded catalog."
                    if skill_names:
                        skill_name_prop["enum"] = skill_names
    return schema
