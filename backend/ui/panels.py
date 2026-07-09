import json
from dataclasses import dataclass

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from backend.ui.text_utils import strip_emojis
from backend.ui.terminal_guard import GuardedStatus

console = Console()

DEFAULT_BORDER = "rgb(165,145,100)"
MUTED_BORDER = "rgb(150,150,150)"
DEFAULT_BODY = "rgb(210,200,200)"


@dataclass(frozen=True)
class PanelSpec:
    icon: str
    label: str
    detail: str = ""
    border_style: str = DEFAULT_BORDER
    body_style: str = DEFAULT_BODY

    @property
    def title(self) -> str:
        detail = f"  {self.detail}" if self.detail else ""
        return f"{self.icon}  {self.label}{detail}"


def tool_color(tool_name: str) -> str:
    return MUTED_BORDER if tool_name == "execute_command" else DEFAULT_BORDER


def agent_action_spec(tool_name: str) -> PanelSpec:
    color = tool_color(tool_name)
    return PanelSpec("⚙", "Agent Action", tool_name, border_style=color, body_style=color)


def agent_observation_spec(tool_name: str, ok: bool = True) -> PanelSpec:
    return PanelSpec("✓" if ok else "✗", "Observation", f"[{tool_name}]", border_style=tool_color(tool_name))


def python_execution_spec(exit_code: int) -> PanelSpec:
    return PanelSpec("✓" if exit_code == 0 else "✗", "Python Execution", f"exit_code={exit_code}", border_style=MUTED_BORDER)


def python_timeout_spec(timeout_sec: int) -> PanelSpec:
    return PanelSpec("⚠", "Python Timeout", f"{timeout_sec}s", border_style=MUTED_BORDER)


def make_panel(
    title: str,
    body: str = "",
    *,
    border_style: str = DEFAULT_BORDER,
    body_style: str = DEFAULT_BODY,
) -> Panel:
    content = Text()
    content.append(title, style=f"bold {border_style}")
    if body:
        content.append("\n\n")
        content.append(body, style=body_style)
    return Panel(content, border_style=border_style, padding=(0, 1))


def make_message_panel(spec: PanelSpec, body: str = "") -> Panel:
    return make_panel(spec.title, body, border_style=spec.border_style, body_style=spec.body_style)


def print_panel(
    title: str,
    body: str = "",
    *,
    border_style: str = DEFAULT_BORDER,
    body_style: str = DEFAULT_BODY,
    leading_blank: bool = False,
) -> None:
    if leading_blank:
        console.print()
    console.print(make_panel(title, body, border_style=border_style, body_style=body_style))


def print_message_panel(spec: PanelSpec, body: str = "", *, leading_blank: bool = False) -> None:
    if leading_blank:
        console.print()
    console.print(make_message_panel(spec, body))


def print_agent_action(tool_name: str, args: dict):
    print_message_panel(
        agent_action_spec(tool_name),
        json.dumps(args, ensure_ascii=False),
        leading_blank=True,
    )


class StreamingObservation:
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self._captured: list[str] = []
        self._display_lines: list[str] = []
        self._line_buffer = ""
        self._closed = False
        self._spec = agent_observation_spec(tool_name)
        self._live = Live(self._render_panel(), console=console, refresh_per_second=12, transient=False)
        self._live.start(refresh=True)

    def _render_panel(self) -> Panel:
        return make_message_panel(self._spec, "\n".join(self._display_lines))

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
    print_message_panel(agent_observation_spec(tool_name, ok), strip_emojis(observation))
    return observation_text


def get_spinner_status(text: str = "Thinking... (esc to cancel)"):
    status = console.status(
        f"[italic {MUTED_BORDER}]{text}[/]",
        spinner="dots",
        spinner_style=MUTED_BORDER,
    )
    return GuardedStatus(status)


def format_execution_body(stdout: str, stderr: str) -> str:
    body_parts = []
    if stdout:
        body_parts.append("[stdout]\n" + stdout)
    if stderr:
        body_parts.append("[stderr]\n" + stderr)
    return "\n".join(body_parts)


def print_python_execution(exit_code: int, stdout: str, stderr: str):
    print_message_panel(python_execution_spec(exit_code), format_execution_body(stdout, stderr))


def print_python_timeout(timeout_sec: int, stdout: str, stderr: str):
    print_message_panel(python_timeout_spec(timeout_sec), format_execution_body(stdout, stderr))
