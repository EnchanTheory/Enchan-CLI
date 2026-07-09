import os
import select
import shutil
import sys
import time

from backend.text_utils import truncate_visual

ANSI_RESET = "\x1b[0m"
ANSI_GOLD = "\x1b[1;38;2;165;145;100m"
ANSI_WHITE = "\x1b[38;2;210;200;200m"
ANSI_WARN = "\x1b[38;2;180;100;100m"

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
