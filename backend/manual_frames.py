"""Width-aware manual frames for streaming tool output.

Rich Panels need complete content up front, but skill output is streamed live.
This module keeps that streaming behavior while removing the old hardcoded
40-column frame used by the manual streaming path.
"""

from __future__ import annotations

import json
import re
import shutil
import sys

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None
    Panel = None
    Text = None

_FRAME_MIN_WIDTH = 40
_FRAME_MAX_WIDTH = 240

_EMOJI_PATTERN = re.compile(
    r'[\U0001F600-\U0001F64F]'
    r'|[\U0001F300-\U0001F5FF]'
    r'|[\U0001F680-\U0001F6FF]'
    r'|[\U0001F700-\U0001F77F]'
    r'|[\U0001F780-\U0001F7FF]'
    r'|[\U0001F800-\U0001F8FF]'
    r'|[\U0001F900-\U0001F9FF]'
    r'|[\U0001FA00-\U0001FA6F]'
    r'|[\U0001FA70-\U0001FAFF]'
    r'|[\u2600-\u26FF]'
    r'|[\u2700-\u27BF]'
    r'|[\uFE0F]'
)


def _strip_emojis(text: str) -> str:
    return _EMOJI_PATTERN.sub("", text)


def _frame_width() -> int:
    columns = shutil.get_terminal_size(fallback=(80, 24)).columns
    return max(_FRAME_MIN_WIDTH, min(columns, _FRAME_MAX_WIDTH))


def _rule() -> str:
    return "─" * max(1, _frame_width() - 1)


def _top(ansi_color: str) -> str:
    return f"\x1b[38;2;{ansi_color}m╭{_rule()}\x1b[0m"


def _bottom(ansi_color: str) -> str:
    return f"\x1b[38;2;{ansi_color}m╰{_rule()}\x1b[0m"


def _line(ansi_color: str, text: str = "", text_color: str | None = None) -> str:
    prefix = f"\x1b[38;2;{ansi_color}m│\x1b[0m"
    if not text:
        return prefix
    if text_color:
        return f"{prefix} \x1b[38;2;{text_color}m{text}\x1b[0m"
    return f"{prefix} {text}"


def _ascii_safe(text: str) -> str:
    return (
        text.replace("╭", "+")
        .replace("╰", "+")
        .replace("│", "|")
        .replace("─", "-")
        .replace("✓", "OK")
        .replace("✗", "X")
        .replace("⚙", "*")
        .replace("⚠", "!")
    )


def _write_stream(stream, text: str) -> None:
    try:
        stream.write(text)
    except UnicodeEncodeError:
        encoding = getattr(stream, "encoding", None) or "utf-8"
        safe = _ascii_safe(text).encode(encoding, errors="replace").decode(encoding, errors="replace")
        stream.write(safe)


def _print_frame_start(ansi_color: str, title: str, *, leading_blank: bool = False) -> None:
    if leading_blank:
        print()
    print(_top(ansi_color))
    print(_line(ansi_color, title))
    print(_line(ansi_color))


def _print_frame_end(ansi_color: str) -> None:
    print(_bottom(ansi_color))


class StreamingObservation:
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self._captured: list[str] = []
        self._line_buffer = ""
        self._closed = False
        self._stream = sys.stdout
        self._ansi_color = "150;150;150" if tool_name == "execute_command" else "165;145;100"
        self._open()

    def _open(self) -> None:
        _write_stream(self._stream, _top(self._ansi_color) + "\n")
        _write_stream(self._stream, _line(self._ansi_color, f"✓  Observation  [{self.tool_name}]") + "\n")
        _write_stream(self._stream, _line(self._ansi_color) + "\n")
        self._stream.flush()

    def _write_display_line(self, line: str) -> None:
        display_line = _strip_emojis(line)
        _write_stream(self._stream, _line(self._ansi_color, display_line, text_color="210;200;200") + "\n")

    def write(self, text: str) -> int:
        if not text:
            return 0
        text = str(text)
        self._captured.append(text)
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        self._line_buffer += normalized
        while "\n" in self._line_buffer:
            line, self._line_buffer = self._line_buffer.split("\n", 1)
            self._write_display_line(line)
        self._stream.flush()
        return len(text)

    def flush(self) -> None:
        self._stream.flush()

    def close(self) -> None:
        if self._closed:
            return
        if self._line_buffer:
            self._write_display_line(self._line_buffer)
            self._line_buffer = ""
        _write_stream(self._stream, _bottom(self._ansi_color) + "\n")
        self._stream.flush()
        self._closed = True

    def getvalue(self) -> str:
        return "".join(self._captured)


def stream_agent_observation(tool_name: str) -> StreamingObservation:
    return StreamingObservation(tool_name)


def print_agent_action(tool_name: str, args: dict):
    color = "rgb(150,150,150)" if tool_name == "execute_command" else "rgb(165,145,100)"
    if RICH_AVAILABLE:
        args_str = json.dumps(args, ensure_ascii=False)
        content = Text()
        content.append(f"⚙  Agent Action  {tool_name}\n\n", style=f"bold {color}")
        content.append(f"{args_str}", style=color)
        console.print()
        console.print(Panel(content, border_style=color, padding=(0, 1)))
        return

    ansi_color = "150;150;150" if tool_name == "execute_command" else "165;145;100"
    _print_frame_start(ansi_color, f"⚙  Agent Action  {tool_name}", leading_blank=True)
    print(_line(ansi_color, json.dumps(args, ensure_ascii=False)))
    _print_frame_end(ansi_color)


def print_agent_observation(tool_name: str, ok: bool, observation: str):
    observation_text = f"Observation: [{tool_name}] ok={ok}\n{observation}"
    display_obs = _strip_emojis(observation)
    icon = "✓" if ok else "✗"
    color_border = "rgb(150,150,150)" if tool_name == "execute_command" else "rgb(165,145,100)"

    if RICH_AVAILABLE:
        content = Text()
        content.append(f"{icon}  Observation  [{tool_name}]\n\n", style=f"bold {color_border}")
        content.append(f"{display_obs}", style="rgb(210,200,200)")
        console.print(Panel(content, border_style=color_border, padding=(0, 1)))
    else:
        ansi_color = "150;150;150" if tool_name == "execute_command" else "165;145;100"
        _print_frame_start(ansi_color, f"{icon}  Observation  [{tool_name}]")
        for line in display_obs.splitlines():
            print(_line(ansi_color, line, text_color="210;200;200"))
        _print_frame_end(ansi_color)
    return observation_text
