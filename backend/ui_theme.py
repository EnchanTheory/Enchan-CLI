import json
import os
import re
import select
import shutil
import sys
import time
import unicodedata

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text


def strip_emojis(text: str) -> str:
    emoji_pattern = re.compile(
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
    return emoji_pattern.sub('', text)


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

ANSI_RESET = "\x1b[0m"
ANSI_GOLD = "\x1b[1;38;2;165;145;100m"
ANSI_WHITE = "\x1b[38;2;210;200;200m"
ANSI_WARN = "\x1b[38;2;180;100;100m"

console = Console()

try:
    import msvcrt
except ImportError:
    msvcrt = None

try:
    from prompt_toolkit.styles import Style
    PROMPT_TOOLKIT_STYLE_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_STYLE_AVAILABLE = False


def make_prompt_style():
    if not PROMPT_TOOLKIT_STYLE_AVAILABLE:
        return None
    return Style.from_dict(PROMPT_TOOLKIT_STYLE)


def styled_input(prompt_text: str, default_val: str = "", completer=None) -> str:
    if PROMPT_TOOLKIT_STYLE_AVAILABLE:
        try:
            from prompt_toolkit import PromptSession
            sub_session = PromptSession(style=make_prompt_style(), completer=completer)
            print(prompt_text, end="", flush=True)
            return sub_session.prompt(default=default_val).strip()
        except (KeyboardInterrupt, EOFError):
            return ""
        except Exception:
            pass
    return input(prompt_text).strip()


def print_response_header(label: str, body: str | None = None, line_char: str = "-") -> None:
    width = shutil.get_terminal_size(fallback=(80, 24)).columns
    print("\n\x1b[90m" + line_char * width + "\x1b[0m")
    if body is None:
        print(f"[{label}]:\n", end="", flush=True)
    else:
        print(f"[{label}]:\n{body}")


def _tool_color(tool_name: str) -> str:
    return "rgb(150,150,150)" if tool_name == "execute_command" else "rgb(165,145,100)"


def _make_panel(
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


def _print_panel(
    title: str,
    body: str = "",
    *,
    border_style: str = "rgb(165,145,100)",
    body_style: str = "rgb(210,200,200)",
    leading_blank: bool = False,
) -> None:
    if leading_blank:
        console.print()
    console.print(_make_panel(title, body, border_style=border_style, body_style=body_style))


def _visual_len(text: str) -> int:
    width = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in "WF" else 1
    return width


def _truncate_visual(text: str, max_width: int) -> str:
    if max_width <= 0:
        return ""
    if _visual_len(text) <= max_width:
        return text
    marker = "..."
    limit = max(0, max_width - len(marker))
    width = 0
    result = ""
    for char in text:
        char_width = 0 if unicodedata.combining(char) else (2 if unicodedata.east_asian_width(char) in "WF" else 1)
        if width + char_width > limit:
            break
        result += char
        width += char_width
    return result + marker


def _read_raw_char(fd: int) -> str:
    ch = os.read(fd, 1).decode(errors="ignore")
    return ch or ""


def _drain_stdin() -> None:
    """Discard pending keypresses so Enter spam cannot leak into the next prompt."""
    if not sys.stdin.isatty():
        return
    try:
        if sys.platform == "win32":
            if msvcrt is None:
                return
            while msvcrt.kbhit():
                msvcrt.getwch()
        else:
            fd = sys.stdin.fileno()
            while True:
                ready, _, _ = select.select([fd], [], [], 0)
                if not ready:
                    break
                os.read(fd, 1024)
    except Exception:
        pass


class _SpinnerInputGuard:
    """Suppress terminal echo while a spinner is active."""

    def __init__(self):
        self._fd: int | None = None
        self._old_settings = None
        self._active = False

    def start(self) -> None:
        if self._active or not sys.stdin.isatty() or sys.platform == "win32":
            return
        try:
            import termios
            import tty

            self._fd = sys.stdin.fileno()
            self._old_settings = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
            new_settings = termios.tcgetattr(self._fd)
            new_settings[3] &= ~termios.ECHO
            termios.tcsetattr(self._fd, termios.TCSANOW, new_settings)
            self._active = True
        except Exception:
            self._fd = None
            self._old_settings = None
            self._active = False

    def stop(self) -> None:
        if sys.platform == "win32":
            _drain_stdin()
            return
        if not self._active or self._fd is None or self._old_settings is None:
            return
        try:
            import termios

            termios.tcflush(self._fd, termios.TCIFLUSH)
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_settings)
        except Exception:
            pass
        finally:
            self._active = False
            self._fd = None
            self._old_settings = None


class GuardedStatus:
    def __init__(self, inner):
        self._inner = inner
        self._guard = _SpinnerInputGuard()

    def start(self):
        self._guard.start()
        return self._inner.start()

    def stop(self):
        try:
            return self._inner.stop()
        finally:
            self._guard.stop()

    def update(self, *args, **kwargs):
        if hasattr(self._inner, "update"):
            return self._inner.update(*args, **kwargs)
        return None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()
        return False


def _draw_menu_lines(options: list[tuple[str, str, bool]], highlighted_idx: int) -> None:
    term_width = shutil.get_terminal_size(fallback=(80, 24)).columns
    for i, (label, desc, ready) in enumerate(options):
        status = "" if ready else " (Unavailable)"
        if i == highlighted_idx:
            cursor = ">"
            color_start = ANSI_GOLD
            bullet = "*"
        else:
            cursor = " "
            color_start = ANSI_WHITE if ready else "\x1b[38;2;120;120;120m"
            bullet = "-"
        line_text = f"  {cursor} {bullet} {label} | {desc}{status}"
        line_text = _truncate_visual(line_text, term_width - 2)
        sys.stdout.write(f"\r\x1b[K{color_start}{line_text}{ANSI_RESET}\n")
    sys.stdout.flush()


def _read_posix_escape_sequence() -> str:
    fd = sys.stdin.fileno()
    seq = "\x1b"
    while True:
        ready, _, _ = select.select([fd], [], [], 0.01)
        if not ready:
            break
        ch = _read_raw_char(fd)
        if not ch:
            break
        seq += ch
        if len(seq) >= 3 and seq[1] in ("[", "O") and seq[-1].isalpha():
            break
        if len(seq) >= 3 and seq[1] == "[" and "@" <= seq[-1] <= "~":
            break
        if len(seq) >= 16:
            break
    return seq


def interactive_menu(title: str, options: list[tuple[str, str, bool]], default_idx: int = 0) -> int:
    """Displays an interactive arrow-key menu."""
    if not options:
        return -1

    selectable_indices = [i for i, (_, _, ready) in enumerate(options) if ready]
    if not selectable_indices:
        return -1
    if default_idx < 0 or default_idx >= len(options) or not options[default_idx][2]:
        default_idx = selectable_indices[0]

    is_interactive = sys.stdin.isatty() and (msvcrt is not None or sys.platform != "win32")

    if not is_interactive:
        print(f"\n[{title}]")
        for i, (label, desc, ready) in enumerate(options, 1):
            marker = "*" if i - 1 == default_idx else " "
            status = "" if ready else " (Unavailable)"
            color_start = "\x1b[38;2;210;200;200m" if ready else "\x1b[38;2;120;120;120m"
            print(f"  {color_start}{i}. {label:<20} {marker} {desc}{status}{ANSI_RESET}")

        default_index = default_idx + 1
        try:
            raw = input(f"Select number [{default_index}] (or Enter to cancel): ").strip()
            if not raw:
                return default_idx
            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < len(options) and options[idx][2]:
                    return idx
            return -1
        except (KeyboardInterrupt, EOFError):
            return -1

    print(f"\n[{title}] (Use Up/Down arrows and press Enter to select)")
    num_options = len(options)
    current_idx = default_idx

    def draw_menu() -> None:
        _draw_menu_lines(options, current_idx)
        sys.stdout.write(f"\x1b[{num_options}A")
        sys.stdout.flush()

    def finish_with(result: int) -> int:
        sys.stdout.write(f"\x1b[{num_options}B\r\n")
        sys.stdout.flush()
        return result

    def move_selection(delta: int) -> None:
        nonlocal current_idx
        orig_idx = current_idx
        while True:
            current_idx = (current_idx + delta) % num_options
            if options[current_idx][2] or current_idx == orig_idx:
                break

    _draw_menu_lines(options, current_idx)
    sys.stdout.write(f"\x1b[{num_options}A")
    sys.stdout.flush()

    try:
        if sys.platform == "win32":
            while True:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key in (b"\x00", b"\xe0"):
                        special_key = msvcrt.getch()
                        if special_key == b"H":
                            move_selection(-1)
                            draw_menu()
                        elif special_key == b"P":
                            move_selection(1)
                            draw_menu()
                        elif special_key in (b"K", b"M"):
                            continue
                    elif key == b"\r":
                        return finish_with(current_idx)
                    elif key in (b"\x03", b"\x1b"):
                        return finish_with(-1)
                else:
                    time.sleep(0.01)
        else:
            import termios
            import tty

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while True:
                    ch = _read_raw_char(fd)
                    if ch == "\x1b":
                        seq = _read_posix_escape_sequence()
                        if seq in ("\x1b[A", "\x1bOA"):
                            move_selection(-1)
                            draw_menu()
                        elif seq in ("\x1b[B", "\x1bOB"):
                            move_selection(1)
                            draw_menu()
                        elif seq in ("\x1b[C", "\x1bOC", "\x1b[D", "\x1bOD"):
                            continue
                        elif seq == "\x1b":
                            return finish_with(-1)
                    elif ch in ("\r", "\n"):
                        return finish_with(current_idx)
                    elif ch == "\x03":
                        return finish_with(-1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)


def interactive_yes_no(prompt: str, default_yes: bool = True) -> bool:
    """Displays a horizontal Yes/No selector."""
    if not sys.stdin.isatty():
        print(f"\n{ANSI_WARN}  [System] Non-interactive shell detected. Denying by default.{ANSI_RESET}")
        return False

    selected_yes = default_yes

    def draw() -> None:
        yes_color = ANSI_GOLD if selected_yes else ANSI_WHITE
        no_color = ANSI_WHITE if selected_yes else ANSI_GOLD
        yes_cursor = ">" if selected_yes else " "
        no_cursor = " " if selected_yes else ">"
        sys.stdout.write("\r\x1b[K")
        sys.stdout.write(f"{ANSI_GOLD}  {prompt} {ANSI_RESET}")
        sys.stdout.write(f"{yes_color} {yes_cursor} [ Yes ] {ANSI_RESET}")
        sys.stdout.write(f"{no_color} {no_cursor} [ No ] {ANSI_RESET}")
        sys.stdout.flush()

    try:
        draw()
        if sys.platform == "win32":
            while True:
                if msvcrt and msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key in (b"\x00", b"\xe0"):
                        special_key = msvcrt.getch()
                        if special_key in (b"K", b"M"):
                            selected_yes = not selected_yes
                            draw()
                    elif key == b"\r":
                        sys.stdout.write("\n")
                        return selected_yes
                    elif key in (b"y", b"Y"):
                        sys.stdout.write("\n")
                        return True
                    elif key in (b"n", b"N", b"\x03"):
                        sys.stdout.write("\n")
                        return False
                else:
                    time.sleep(0.01)
        else:
            import termios
            import tty

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while True:
                    ch = _read_raw_char(fd)
                    if ch == "\x1b":
                        seq = _read_posix_escape_sequence()
                        if seq in ("\x1b[D", "\x1bOD", "\x1b[C", "\x1bOC"):
                            selected_yes = not selected_yes
                            draw()
                        elif seq == "\x1b":
                            sys.stdout.write("\r\n")
                            return False
                    elif ch in ("\r", "\n"):
                        sys.stdout.write("\r\n")
                        return selected_yes
                    elif ch.lower() == "y":
                        sys.stdout.write("\r\n")
                        return True
                    elif ch.lower() == "n" or ch == "\x03":
                        sys.stdout.write("\r\n")
                        return False
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)


def print_agent_action(tool_name: str, args: dict):
    color = _tool_color(tool_name)
    _print_panel(
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
        self._color = _tool_color(tool_name)
        self._live = Live(self._render_panel(), console=console, refresh_per_second=12, transient=False)
        self._live.start(refresh=True)

    def _render_panel(self) -> Panel:
        body = "\n".join(self._display_lines)
        return _make_panel(f"✓  Observation  [{self.tool_name}]", body, border_style=self._color)

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
    display_obs = strip_emojis(observation)
    icon = "✓" if ok else "✗"
    _print_panel(f"{icon}  Observation  [{tool_name}]", display_obs, border_style=_tool_color(tool_name))
    return observation_text


class DummyStatus:
    def __init__(self, text):
        self.text = text
        self._guard = _SpinnerInputGuard()

    def start(self):
        self._guard.start()
        print(f"\x1b[3;38;2;150;150;150m{self.text}\x1b[0m", end="", flush=True)

    def stop(self):
        try:
            print("\r\x1b[K", end="", flush=True)
        finally:
            self._guard.stop()

    def update(self, text):
        self.text = text
        print("\r\x1b[K", end="", flush=True)
        print(f"\x1b[3;38;2;150;150;150m{self.text}\x1b[0m", end="", flush=True)


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
    _print_panel(title, "\n".join(body_parts), border_style="rgb(150,150,150)")


def print_python_execution(exit_code: int, stdout: str, stderr: str):
    icon = "✓" if exit_code == 0 else "✗"
    _print_execution_panel(f"{icon}  Python Execution  exit_code={exit_code}", stdout, stderr)


def print_python_timeout(timeout_sec: int, stdout: str, stderr: str):
    _print_execution_panel(f"⚠  Python Timeout  {timeout_sec}s", stdout, stderr)
