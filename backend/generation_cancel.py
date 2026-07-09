"""Cross-platform terminal input helpers for generation cancellation.

The streaming backends advertise ``Esc`` as the cancel key.  Windows can poll
that key with ``msvcrt`` directly, but POSIX terminals need to be placed in a
non-canonical no-echo mode first; otherwise a bare Esc is line-buffered and the
streaming loop never sees it.

This module intentionally owns the low-level keyboard behavior so the backends
do not each grow slightly different Windows/macOS/Linux implementations.
"""

from __future__ import annotations

import os
import select
import sys

try:
    import msvcrt
except ImportError:  # pragma: no cover - non-Windows platforms
    msvcrt = None


_ESCAPE_SEQUENCE_PREFIXES = (b"[", b"O")
_MAX_ESCAPE_SEQUENCE_BYTES = 16
_ESCAPE_FOLLOW_TIMEOUT_SEC = 0.015
_ESCAPE_DRAIN_TIMEOUT_SEC = 0.002


def _stdin_fd() -> int | None:
    try:
        if not sys.stdin.isatty():
            return None
        return sys.stdin.fileno()
    except Exception:
        return None


def _drain_posix_escape_sequence(fd: int) -> None:
    """Consume the tail of a CSI/SS3 escape sequence without blocking.

    Arrow keys and many terminal function keys begin with ``ESC [`` or ``ESC O``.
    Treating the first byte as cancel would make arrow keys cancel generation, so
    once such a prefix is detected we drain the rest of the sequence and ignore it.
    """

    for _ in range(_MAX_ESCAPE_SEQUENCE_BYTES):
        ready, _, _ = select.select([fd], [], [], _ESCAPE_DRAIN_TIMEOUT_SEC)
        if not ready:
            break
        chunk = os.read(fd, 1)
        if not chunk:
            break
        byte = chunk[0]
        # ASCII letters and final bytes in CSI sequences terminate the key code.
        if 0x40 <= byte <= 0x7E:
            break


def _posix_esc_pressed() -> bool:
    fd = _stdin_fd()
    if fd is None:
        return False

    pressed = False
    try:
        while True:
            ready, _, _ = select.select([fd], [], [], 0)
            if not ready:
                break

            chunk = os.read(fd, 1)
            if not chunk:
                break
            if chunk != b"\x1b":
                # Discard accidental keypresses typed during generation so they do
                # not leak into the next prompt when the guard is released.
                continue

            # A bare Esc has no following byte.  Arrow/function keys emit an
            # escape sequence immediately after Esc, so wait a tiny amount to
            # distinguish the two without making polling feel sticky.
            ready, _, _ = select.select([fd], [], [], _ESCAPE_FOLLOW_TIMEOUT_SEC)
            if not ready:
                pressed = True
                continue

            next_byte = os.read(fd, 1)
            if next_byte in _ESCAPE_SEQUENCE_PREFIXES:
                _drain_posix_escape_sequence(fd)
                continue

            # Alt/meta key combinations also begin with Esc but are not the
            # advertised cancel key.  Consume the pair and ignore it.
    except Exception:
        return pressed
    return pressed


def _windows_esc_pressed() -> bool:
    if msvcrt is None:
        return False

    pressed = False
    try:
        while msvcrt.kbhit():
            key = msvcrt.getwch()
            if key == "\x1b":
                pressed = True
            elif key in ("\x00", "\xe0") and msvcrt.kbhit():
                # Discard the second byte of Windows extended keys so arrows do
                # not leave pending input behind.
                msvcrt.getwch()
    except Exception:
        return pressed
    return pressed


def esc_pressed() -> bool:
    """Return True once if the user pressed bare Esc during generation.

    Non-Esc keypresses are deliberately consumed.  While a generation is in
    progress, typed characters are not useful input; keeping them would make them
    appear in the next prompt after cancellation/completion.
    """

    if sys.platform == "win32":
        return _windows_esc_pressed()
    return _posix_esc_pressed()


def drain_stdin() -> None:
    """Discard pending terminal input before returning to the prompt."""

    if sys.platform == "win32":
        _windows_esc_pressed()
        if msvcrt is None:
            return
        try:
            while msvcrt.kbhit():
                msvcrt.getwch()
        except Exception:
            pass
        return

    fd = _stdin_fd()
    if fd is None:
        return
    try:
        while True:
            ready, _, _ = select.select([fd], [], [], 0)
            if not ready:
                break
            os.read(fd, 1024)
    except Exception:
        pass


class GenerationInputGuard:
    """Hold POSIX stdin in cbreak/no-echo mode for a streaming generation.

    The guard is intentionally independent from the spinner guard.  Start it
    before the spinner starts; nested spinner guards then snapshot the already
    guarded terminal state and cannot accidentally restore canonical mode while
    the response body is still streaming.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._fd: int | None = None
        self._old_settings = None
        self._active = False

    def start(self) -> None:
        if not self.enabled or self._active or sys.platform == "win32":
            return
        fd = _stdin_fd()
        if fd is None:
            return
        try:
            import termios
            import tty

            self._fd = fd
            self._old_settings = termios.tcgetattr(fd)
            tty.setcbreak(fd)
            new_settings = termios.tcgetattr(fd)
            new_settings[3] &= ~termios.ECHO
            termios.tcsetattr(fd, termios.TCSANOW, new_settings)
            self._active = True
        except Exception:
            self._fd = None
            self._old_settings = None
            self._active = False

    def stop(self) -> None:
        if sys.platform == "win32":
            drain_stdin()
            return
        if not self._active or self._fd is None or self._old_settings is None:
            return
        try:
            import termios

            drain_stdin()
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_settings)
        except Exception:
            pass
        finally:
            self._active = False
            self._fd = None
            self._old_settings = None

    def __enter__(self) -> "GenerationInputGuard":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.stop()
        return False
