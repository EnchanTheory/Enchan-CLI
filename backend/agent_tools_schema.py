import copy
from typing import Any

AGENT_TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "host_shell",
            "description": "Executes terminal commands with the OS-native default shell. Use this for git, python, npm, tests, diagnostics, builds, etc.",
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
            "name": "list_directory",
            "description": "Lists the contents of a directory to a specified depth.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path to the directory"},
                    "depth": {"type": "integer", "description": "Maximum depth to recurse (optional, default 2)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_document",
            "description": "Reads a file. Supports line-range reading or content summarization/compression.",
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
            "description": "Searches for a regular expression pattern across all files in the workspace.",
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
            "description": "Creates a new UTF-8 text file or completely overwrites an existing one.",
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
            "description": "Applies a unified diff patch to the workspace.",
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
            "name": "git_status",
            "description": "Runs 'git status --short' to show working tree status.",
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
            "name": "git_diff",
            "description": "Runs 'git diff' to show changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "staged": {"type": "boolean", "description": "Set to true to diff staged changes (--cached)"},
                    "paths": {"type": "array", "items": {"type": "string"}, "description": "Specific file paths to diff (optional)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_add",
            "description": "Runs 'git add' to stage files for commit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paths": {"type": "array", "items": {"type": "string"}, "description": "List of paths to stage"}
                },
                "required": ["paths"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Runs 'git commit' to commit staged changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The commit message"}
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Finds candidate web pages only. Prefer web_browse for web/news questions because web_browse opens pages and returns readable page text.",
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
            "description": "Browses the web by opening a URL or by finding and opening pages for a query. Use this for current news, site contents, and any answer that needs page text rather than search snippets.",
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
            "description": "Lists the full registered skill catalog, including method schemas. Use for expanded detail only; installed skills are already auto-surfaced in the agent context and use_skill schema.",
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
            "description": "Delegates a complex prompt or task to an external agent model (e.g. codex, gemini, claude).",
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


def _tighten_tool_argument_schema(parameters: dict[str, Any]) -> None:
    """Make top-level tool arguments closed without affecting nested free-form params.

    llama.cpp and Ollama already receive the tool schema from each request. Closing the
    top-level argument object gives constrained decoders a stricter target and reduces
    out-of-schema keys from small models, while keeping normal prose responses untouched.
    The nested use_skill.params object intentionally remains open because skill methods
    have their own dynamic schemas.
    """
    if not isinstance(parameters, dict):
        return
    if parameters.get("type") != "object":
        return
    if not isinstance(parameters.get("properties"), dict):
        return
    parameters.setdefault("additionalProperties", False)


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
        parameters = function.get("parameters")
        if isinstance(parameters, dict):
            _tighten_tool_argument_schema(parameters)
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
