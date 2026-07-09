import json

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from backend.text_utils import strip_emojis
from backend.terminal_guard import GuardedStatus

console = Console()


def tool_color(tool_name: str) -> str:
    return "rgb(150,150,150)" if tool_name == "execute_command" else "rgb(165,145,100)"


def make_panel(
    title: str,
    body: str = "",
    *,
    border_style: str = "rgb(165,145,100)",
    body_style: str = "rgb(210,200,200)",
) -> Panel:
    content = Text()
    content.append(title, style=f"bold {border_style}")
    if body:
        content.append("\n\n")
        content.append(body, style=body_style)
    return Panel(content, border_style=border_style, padding=(0, 1))


def print_panel(
    title: str,
    body: str = "",
    *,
    border_style: str = "rgb(165,145,100)",
    body_style: str = "rgb(210,200,200)",
    leading_blank: bool = False,
) -> None:
    if leading_blank:
        console.print()
    console.print(make_panel(title, body, border_style=border_style, body_style=body_style))


def print_agent_action(tool_name: str, args: dict):
    color = tool_color(tool_name)
    print_panel(
        f"⚙  Agent Action  {tool_name}",
        json.dumps(args, ensure_ascii=False),
        border_style=color,
        body_style=color,
        leading_blank=True,
    )


class StreamingObservation:
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self._captured: list[str] = []
        self._display_lines: list[str] = []
        self._line_buffer = ""
        self._closed = False
        self._color = tool_color(tool_name)
        self._live = Live(self._render_panel(), console=console, refresh_per_second=12, transient=False)
        self._live.start(refresh=True)

    def _render_panel(self) -> Panel:
        body = "\n".join(self._display_lines)
        return make_panel(f"✓  Observation  [{self.tool_name}]", body, border_style=self._color)

    def _write_display_line(self, line: str) -> None:
        self._display_lines.append(strip_emojis(line))
        self._live.update(self._render_panel(), refresh=True)

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
        return len(text)

    def flush(self) -> None:
        return None

    def close(self) -> None:
        if self._closed:
            return
        if self._line_buffer:
            self._write_display_line(self._line_buffer)
            self._line_buffer = ""
        self._live.update(self._render_panel(), refresh=True)
        self._live.stop()
        self._closed = True

    def getvalue(self) -> str:
        return "".join(self._captured)


def stream_agent_observation(tool_name: str) -> StreamingObservation:
    return StreamingObservation(tool_name)


def print_agent_observation(tool_name: str, ok: bool, observation: str):
    observation_text = f"Observation: [{tool_name}] ok={ok}\n{observation}"
    icon = "✓" if ok else "✗"
    print_panel(f"{icon}  Observation  [{tool_name}]", strip_emojis(observation), border_style=tool_color(tool_name))
    return observation_text


def get_spinner_status(text: str = "Thinking... (esc to cancel)"):
    status = console.status(
        f"[italic rgb(150,150,150)]{text}[/]",
        spinner="dots",
        spinner_style="rgb(150,150,150)",
    )
    return GuardedStatus(status)


def _print_execution_panel(title: str, stdout: str, stderr: str) -> None:
    body_parts = []
    if stdout:
        body_parts.append("[stdout]\n" + stdout)
    if stderr:
        body_parts.append("[stderr]\n" + stderr)
    print_panel(title, "\n".join(body_parts), border_style="rgb(150,150,150)")


def print_python_execution(exit_code: int, stdout: str, stderr: str):
    icon = "✓" if exit_code == 0 else "✗"
    _print_execution_panel(f"{icon}  Python Execution  exit_code={exit_code}", stdout, stderr)


def print_python_timeout(timeout_sec: int, stdout: str, stderr: str):
    _print_execution_panel(f"⚠  Python Timeout  {timeout_sec}s", stdout, stderr)
