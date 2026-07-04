import os
import sys
import shutil
import urllib.request
import json
import re
from pathlib import Path
from typing import Optional

# Path Resolution
BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent


from backend.ui_theme import interactive_menu, styled_input

from backend.session_log import (
    append_session_event,
    list_session_logs,
    load_session_messages,
    resolve_session_log,
    get_session_metadata,
)


NATURAL_LANGUAGE_ARG_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff01-\uff5e]|[。、「」？]")


def looks_like_natural_language_arg(value: str) -> bool:
    if not value:
        return False
    return bool(NATURAL_LANGUAGE_ARG_RE.search(value))


def print_cli_help():
    """Deprecated fallback helper. Commands are now declarative in registry."""
    from backend.commands.general import handle_help
    handle_help(file_context="")

def print_license():
    """Deprecated fallback helper. Commands are now declarative in registry."""
    from backend.commands.general import handle_license
    handle_license(file_context="")

def handle_cli_command(
    user_input: str,
    chat_history: list[dict],
    file_context: str,
    loaded_files: list[str],
    generation_config: dict,
    model=None,
    session_log_path: Path | None = None,
    agent_mode: bool = False,
    memory_recorder=None,
    tokenizer=None,
) -> tuple[bool, str, bool]:
    """Dynamically dispatches slash commands to declarative core registry handlers."""
    parts = user_input.strip().split()
    if not parts:
        return False, file_context, False
        
    command = parts[0].lower()
    
    # Lazy Import the commands packages so everything is self-registered inside registry
    from backend.commands import registry
    
    if command in registry.commands:
        context = {
            "user_input": user_input,
            "chat_history": chat_history,
            "file_context": file_context,
            "loaded_files": loaded_files,
            "generation_config": generation_config,
            "model": model,
            "session_log_path": session_log_path,
            "agent_mode": agent_mode,
            "memory_recorder": memory_recorder,
            "tokenizer": tokenizer,
        }
        return registry.commands[command].handler(**context)
        
    print(f"[Error] Unknown command: {command}. Type /help for available commands.")
    return True, file_context, False
