import copy
from typing import Any

AGENT_TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "host_shell",
            "description": "Executes terminal commands with the OS-native default shell. Use this for git, directory listing, python, npm, tests, diagnostics, builds, and other command-line work. This is the general command surface; do not use narrower git/listing wrappers.",
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
            "name": "read_document",
            "description": "Reads a file. Use line ranges for precise code work; use mode='compress' only for large files or summarization/extraction.",
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
            "name": "search_pattern",
            "description": "Searches for a regular expression pattern across files in the workspace. Use this before broad file reads when locating code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "regex": {"type": "string", "description": "The regular expression to search for"}
                },
                "required": ["regex"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "replace_text",
            "description": "Edits a file by replacing an exact string match. Use apply=false for a dry run to check the diff before applying.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path to the file to edit"},
                    "old": {"type": "string", "description": "The exact existing text to replace. Must match exactly once in the file."},
                    "new": {"type": "string", "description": "The new text to insert"},
                    "apply": {"type": "boolean", "description": "Set to true to apply the edit. False performs a dry-run (diff)."}
                },
                "required": ["path", "old", "new"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_text_file",
            "description": "Creates a new UTF-8 text file or completely overwrites an existing one. Prefer replace_text or apply_patch for normal code edits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path to the file"},
                    "content": {"type": "string", "description": "The complete new content of the file"},
                    "overwrite": {"type": "boolean", "description": "Set to true to overwrite if the file already exists"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "apply_patch",
            "description": "Applies a unified diff patch to the workspace. Prefer this for multi-line or multi-file code edits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patch": {"type": "string", "description": "The unified diff patch string"}
                },
                "required": ["patch"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Finds candidate web pages only. Keep this because web research is a unique capability, not a duplicate of local code tools. Prefer web_browse when readable page text is needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_browse",
            "description": "Browses the web by opening a URL or by finding and opening pages for a query. Keep this because web reading is a unique capability, not a duplicate of local code tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "HTTP(S) URL to open directly (optional if query is provided)"},
                    "query": {"type": "string", "description": "Query to find and open relevant pages (optional if url is provided)"},
                    "max_pages": {"type": "integer", "description": "Maximum pages to open for a query (optional, default 3)"},
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
