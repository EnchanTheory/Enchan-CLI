import shutil

from prompt_toolkit.styles import Style

from backend.terminal_input import (
    ANSI_GOLD,
    ANSI_RESET,
    ANSI_WARN,
    ANSI_WHITE,
    interactive_menu,
    interactive_yes_no,
)
from backend.text_utils import strip_emojis, truncate_visual, visual_len
from backend.ui_panels import (
    console,
    get_spinner_status,
    print_agent_action,
    print_agent_observation,
    print_panel,
    print_python_execution,
    print_python_timeout,
    stream_agent_observation,
)

PROMPT_TOOLKIT_STYLE = {
    "bottom-toolbar": "noinherit bg:default fg:default",
    "completion-menu": "bg:#2a2a2a fg:#d2c8c8",
    "completion-menu.completion": "bg:#2a2a2a fg:#d2c8c8",
    "completion-menu.completion.current": "bg:#a59164 fg:#121212 bold",
    "completion-menu.meta.completion": "bg:#222222 fg:#969696",
    "completion-menu.meta.completion.current": "bg:#a59164 fg:#121212 bold",
    "scrollbar.background": "bg:#1e1e1e",
    "scrollbar.button": "bg:#a59164",
}


def make_prompt_style():
    return Style.from_dict(PROMPT_TOOLKIT_STYLE)


def styled_input(prompt_text: str, default_val: str = "", completer=None) -> str:
    try:
        from prompt_toolkit import PromptSession

        sub_session = PromptSession(style=make_prompt_style(), completer=completer)
        print(prompt_text, end="", flush=True)
        return sub_session.prompt(default=default_val).strip()
    except (KeyboardInterrupt, EOFError):
        return ""
    except Exception:
        return input(prompt_text).strip()


def print_response_header(label: str, body: str | None = None, line_char: str = "-") -> None:
    width = shutil.get_terminal_size(fallback=(80, 24)).columns
    print("\n\x1b[90m" + line_char * width + "\x1b[0m")
    if body is None:
        print(f"[{label}]:\n", end="", flush=True)
    else:
        print(f"[{label}]:\n{body}")


__all__ = [
    "ANSI_GOLD",
    "ANSI_RESET",
    "ANSI_WARN",
    "ANSI_WHITE",
    "PROMPT_TOOLKIT_STYLE",
    "console",
    "get_spinner_status",
    "interactive_menu",
    "interactive_yes_no",
    "make_prompt_style",
    "print_agent_action",
    "print_agent_observation",
    "print_panel",
    "print_python_execution",
    "print_python_timeout",
    "print_response_header",
    "stream_agent_observation",
    "strip_emojis",
    "styled_input",
    "truncate_visual",
    "visual_len",
]
