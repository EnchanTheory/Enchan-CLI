import os
import select
import shutil
import sys
import time
from collections.abc import Callable
from typing import TypeVar

from backend.ui.text_utils import truncate_visual

ANSI_RESET = "\x1b[0m"
ANSI_GOLD = "\x1b[1;38;2;165;145;100m"
ANSI_WHITE = "\x1b[38;2;210;200;200m"
ANSI_WARN = "\x1b[38;2;180;100;100m"

KEY_UP = "up"
KEY_DOWN = "down"
KEY_LEFT = "left"
KEY_RIGHT = "right"
KEY_ENTER = "enter"
KEY_ESCAPE = "escape"
KEY_INTERRUPT = "interrupt"
KEY_YES = "yes"
KEY_NO = "no"
KEY_OTHER = "other"

T = TypeVar("T")

try:
    import msvcrt
except ImportError:
    msvcrt = None


def _read_raw_char(fd: int) -> str:
    ch = os.read(fd, 1).decode(errors="ignore")
    return ch or ""


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


def _read_windows_key() -> str:
    while True:
        if not (msvcrt and msvcrt.kbhit()):
            time.sleep(0.01)
            continue
        key = msvcrt.getch()
        if key in (b"\x00", b"\xe0"):
            special_key = msvcrt.getch()
            return {
                b"H": KEY_UP,
                b"P": KEY_DOWN,
                b"K": KEY_LEFT,
                b"M": KEY_RIGHT,
            }.get(special_key, KEY_OTHER)
        if key == b"\r":
            return KEY_ENTER
        if key == b"\x1b":
            return KEY_ESCAPE
        if key == b"\x03":
            return KEY_INTERRUPT
        if key in (b"y", b"Y"):
            return KEY_YES
        if key in (b"n", b"N"):
            return KEY_NO
        return KEY_OTHER


def _read_posix_key() -> str:
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = _read_raw_char(fd)
        if ch == "\x1b":
            seq = _read_posix_escape_sequence()
            return {
                "\x1b[A": KEY_UP,
                "\x1bOA": KEY_UP,
                "\x1b[B": KEY_DOWN,
                "\x1bOB": KEY_DOWN,
                "\x1b[D": KEY_LEFT,
                "\x1bOD": KEY_LEFT,
                "\x1b[C": KEY_RIGHT,
                "\x1bOC": KEY_RIGHT,
                "\x1b": KEY_ESCAPE,
            }.get(seq, KEY_OTHER)
        if ch in ("\r", "\n"):
            return KEY_ENTER
        if ch == "\x03":
            return KEY_INTERRUPT
        if ch.lower() == "y":
            return KEY_YES
        if ch.lower() == "n":
            return KEY_NO
        return KEY_OTHER
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _read_key() -> str:
    if sys.platform == "win32":
        return _read_windows_key()
    return _read_posix_key()


def _run_key_loop(handle_key: Callable[[str], T | None]) -> T:
    try:
        while True:
            result = handle_key(_read_key())
            if result is not None:
                return result
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)


def _finish_inline_prompt(result: T) -> T:
    sys.stdout.write("\r\n")
    return result


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
        line_text = truncate_visual(line_text, term_width - 2)
        sys.stdout.write(f"\r\x1b[K{color_start}{line_text}{ANSI_RESET}\n")
    sys.stdout.flush()


def _is_interactive_terminal() -> bool:
    return sys.stdin.isatty() and (msvcrt is not None or sys.platform != "win32")


def _selectable_indices(options: list[tuple[str, str, bool]]) -> list[int]:
    return [i for i, (_, _, ready) in enumerate(options) if ready]


def _normalized_default_idx(options: list[tuple[str, str, bool]], default_idx: int) -> int:
    selectable_indices = _selectable_indices(options)
    if not selectable_indices:
        return -1
    if default_idx < 0 or default_idx >= len(options) or not options[default_idx][2]:
        return selectable_indices[0]
    return default_idx


def _prompt_menu_number(title: str, options: list[tuple[str, str, bool]], default_idx: int) -> int:
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


def interactive_menu(title: str, options: list[tuple[str, str, bool]], default_idx: int = 0) -> int:
    """Displays an interactive arrow-key menu."""
    if not options:
        return -1

    current_idx = _normalized_default_idx(options, default_idx)
    if current_idx < 0:
        return -1

    if not _is_interactive_terminal():
        return _prompt_menu_number(title, options, current_idx)

    print(f"\n[{title}] (Use Up/Down arrows and press Enter to select)")
    num_options = len(options)

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

    def handle_key(key: str) -> int | None:
        if key == KEY_UP:
            move_selection(-1)
            draw_menu()
        elif key == KEY_DOWN:
            move_selection(1)
            draw_menu()
        elif key == KEY_ENTER:
            return finish_with(current_idx)
        elif key in (KEY_ESCAPE, KEY_INTERRUPT):
            return finish_with(-1)
        return None

    _draw_menu_lines(options, current_idx)
    sys.stdout.write(f"\x1b[{num_options}A")
    sys.stdout.flush()
    return _run_key_loop(handle_key)


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

    def handle_key(key: str) -> bool | None:
        nonlocal selected_yes
        if key in (KEY_LEFT, KEY_RIGHT):
            selected_yes = not selected_yes
            draw()
        elif key == KEY_ENTER:
            return _finish_inline_prompt(selected_yes)
        elif key == KEY_YES:
            return _finish_inline_prompt(True)
        elif key in (KEY_NO, KEY_ESCAPE, KEY_INTERRUPT):
            return _finish_inline_prompt(False)
        return None

    draw()
    return _run_key_loop(handle_key)
