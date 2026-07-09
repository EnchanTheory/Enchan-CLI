import json
import os
import re
import select
import shutil
import sys
import time
import unicodedata


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

_MANUAL_FRAME_MIN_WIDTH = 40
_MANUAL_FRAME_MAX_WIDTH = 240
_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

try:
    import msvcrt
except ImportError:
    msvcrt = None

try:
    from prompt_toolkit.styles import Style
    PROMPT_TOOLKIT_STYLE_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_STYLE_AVAILABLE = False

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


def _visible_text(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _visual_len(text: str) -> int:
    width = 0
    for char in _visible_text(text):
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


def _pad_visual(text: str, width: int) -> str:
    return text + " " * max(0, width - _visual_len(text))


def _manual_frame_width() -> int:
    columns = shutil.get_terminal_size(fallback=(80, 24)).columns
    return max(_MANUAL_FRAME_MIN_WIDTH, min(columns, _MANUAL_FRAME_MAX_WIDTH))


def _manual_frame_inner_width() -> int:
    return max(1, _manual_frame_width() - 4)


def _manual_frame_rule() -> str:
    return "─" * max(1, _manual_frame_width() - 2)


def _manual_frame_top(ansi_color: str) -> str:
    return f"\x1b[38;2;{ansi_color}m╭{_manual_frame_rule()}╮\x1b[0m"


def _manual_frame_bottom(ansi_color: str) -> str:
    return f"\x1b[38;2;{ansi_color}m╰{_manual_frame_rule()}╯\x1b[0m"


def _manual_frame_line(ansi_color: str, text: str = "", text_color: str | None = None) -> str:
    inner_width = _manual_frame_inner_width()
    content = _pad_visual(_truncate_visual(str(text), inner_width), inner_width)
    border = f"\x1b[38;2;{ansi_color}m"
    if text_color and text:
        content = f"\x1b[38;2;{text_color}m{content}\x1b[0m"
    return f"{border}│\x1b[0m {content} {border}│\x1b[0m"


def _manual_frame_print_start(ansi_color: str, title: str, *, leading_blank: bool = False) -> None:
    if leading_blank:
        print()
    print(_manual_frame_top(ansi_color))
    print(_manual_frame_line(ansi_color, title))
    print(_manual_frame_line(ansi_color))


def _manual_frame_print_end(ansi_color: str) -> None:
    print(_manual_frame_bottom(ansi_color))


def _ascii_safe_manual_frame_text(text: str) -> str:
    return (
        text.replace("╭", "+")
        .replace("╮", "+")
        .replace("╰", "+")
        .replace("╯", "+")
        .replace("│", "|")
        .replace("─", "-")
        .replace("✓", "OK")
        .replace("✗", "X")
        .replace("⚙", "*")
        .replace("⚠", "!")
    )


def _write_raw_ascii_safe(stream, text: str) -> None:
    try:
        stream.write(text)
    except UnicodeEncodeError:
        encoding = getattr(stream, "encoding", None) or "utf-8"
        safe_text = _ascii_safe_manual_frame_text(text).encode(encoding, errors="replace").decode(encoding, errors="replace")
        stream.write(safe_text)


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
    def truncate_visual(text: str, max_width: int) -> str:
        return _truncate_visual(text, max_width)

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
        line_text = truncate_visual(line_text, term_width - 2)
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
    _manual_frame_print_start(ansi_color, f"⚙  Agent Action  {tool_name}", leading_blank=True)
    print(_manual_frame_line(ansi_color, json.dumps(args, ensure_ascii=False)))
    _manual_frame_print_end(ansi_color)


class StreamingObservation:
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self._captured: list[str] = []
        self._line_buffer = ""
        self._closed = False
        self._stream = sys.stdout
        self._ansi_color = "150;150;150" if tool_name == "execute_command" else "165;145;100"
        self._open()

    def _write_raw(self, text: str) -> None:
        _write_raw_ascii_safe(self._stream, text)

    def _open(self) -> None:
        self._write_raw(_manual_frame_top(self._ansi_color) + "\n")
        self._write_raw(_manual_frame_line(self._ansi_color, f"✓  Observation  [{self.tool_name}]") + "\n")
        self._write_raw(_manual_frame_line(self._ansi_color) + "\n")
        self._stream.flush()

    def _write_display_line(self, line: str) -> None:
        display_line = strip_emojis(line)
        self._write_raw(_manual_frame_line(self._ansi_color, display_line, text_color="210;200;200") + "\n")

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
        self._write_raw(_manual_frame_bottom(self._ansi_color) + "\n")
        self._stream.flush()
        self._closed = True

    def getvalue(self) -> str:
        return "".join(self._captured)


def stream_agent_observation(tool_name: str) -> StreamingObservation:
    return StreamingObservation(tool_name)


def print_agent_observation(tool_name: str, ok: bool, observation: str):
    observation_text = f"Observation: [{tool_name}] ok={ok}\n{observation}"
    display_obs = strip_emojis(observation)
    icon = "✓" if ok else "✗"
    color_border = "rgb(150,150,150)" if tool_name == "execute_command" else "rgb(165,145,100)"

    if RICH_AVAILABLE:
        content = Text()
        content.append(f"{icon}  Observation  [{tool_name}]\n\n", style=f"bold {color_border}")
        content.append(f"{display_obs}", style="rgb(210,200,200)")
        console.print(Panel(content, border_style=color_border, padding=(0, 1)))
    else:
        ansi_color = "150;150;150" if tool_name == "execute_command" else "165;145;100"
        _manual_frame_print_start(ansi_color, f"{icon}  Observation  [{tool_name}]")
        for line in display_obs.splitlines():
            print(_manual_frame_line(ansi_color, line, text_color="210;200;200"))
        _manual_frame_print_end(ansi_color)
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
    if RICH_AVAILABLE:
        status = console.status(
            f"[italic rgb(150,150,150)]{text}[/]",
            spinner="dots",
            spinner_style="rgb(150,150,150)",
        )
        return GuardedStatus(status)
    return DummyStatus(text)


def _print_execution_panel(title: str, stdout: str, stderr: str) -> None:
    if RICH_AVAILABLE:
        content = Text()
        content.append(f"{title}\n\n", style="bold rgb(150,150,150)")
        if stdout:
            content.append("[stdout]\n", style="rgb(150,150,150)")
            content.append(f"{stdout}\n", style="rgb(210,200,200)")
        if stderr:
            content.append("[stderr]\n", style="rgb(180,100,100)")
            content.append(f"{stderr}\n", style="rgb(180,100,100)")
        if len(content) > 0 and str(content)[-1] == "\n":
            content.right_crop(1)
        console.print(Panel(content, border_style="rgb(150,150,150)", padding=(0, 1)))
        return

    ansi_color = "150;150;150"
    _manual_frame_print_start(ansi_color, title)
    if stdout:
        print(_manual_frame_line(ansi_color, "[stdout]", text_color="150;150;150"))
        for line in stdout.splitlines():
            print(_manual_frame_line(ansi_color, line, text_color="210;200;200"))
    if stderr:
        print(_manual_frame_line(ansi_color, "[stderr]", text_color="180;100;100"))
        for line in stderr.splitlines():
            print(_manual_frame_line(ansi_color, line, text_color="180;100;100"))
    _manual_frame_print_end(ansi_color)


def print_python_execution(exit_code: int, stdout: str, stderr: str):
    icon = "✓" if exit_code == 0 else "✗"
    _print_execution_panel(f"{icon}  Python Execution  exit_code={exit_code}", stdout, stderr)


def print_python_timeout(timeout_sec: int, stdout: str, stderr: str):
    _print_execution_panel(f"⚠  Python Timeout  {timeout_sec}s", stdout, stderr)
