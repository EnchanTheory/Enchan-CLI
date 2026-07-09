import os
import select
import sys

try:
    import msvcrt
except ImportError:
    msvcrt = None


def drain_stdin() -> None:
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


class SpinnerInputGuard:
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
            drain_stdin()
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
        self._guard = SpinnerInputGuard()

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
