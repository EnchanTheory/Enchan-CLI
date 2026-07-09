import subprocess
import ctypes
import sys
import threading
import socket
import time
import signal


CREATE_NEW_PROCESS_GROUP = 0x00000200


def terminate_child(p):
    if p is None or p.poll() is not None:
        return

    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.GenerateConsoleCtrlEvent(1, p.pid)
        except Exception:
            pass
    else:
        try:
            p.terminate()
        except Exception:
            pass

    try:
        p.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/pid", str(p.pid), "/t", "/f"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            try:
                p.kill()
            except Exception:
                pass


def listen_for_shutdown(port, p):
    s = None
    try:
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', port))
        s.listen(1)
        # We only expect one connection ever
        conn, addr = s.accept()
        try:
            conn.recv(1024)
        finally:
            conn.close()
    except Exception:
        pass
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass

    terminate_child(p)


def main():
    if len(sys.argv) < 3:
        sys.exit(1)

    port = int(sys.argv[1])
    cmd = sys.argv[2:]

    popen_kwargs = {}
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = CREATE_NEW_PROCESS_GROUP
    p = subprocess.Popen(cmd, **popen_kwargs)

    shutting_down = False

    def handle_signal(signum, frame):
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        terminate_child(p)
        sys.exit(0)

    for sig in (signal.SIGTERM, signal.SIGINT, getattr(signal, "SIGHUP", None)):
        if sig is not None:
            try:
                signal.signal(sig, handle_signal)
            except Exception:
                pass

    t = threading.Thread(target=listen_for_shutdown, args=(port, p), daemon=True)
    t.start()

    # Wait for the main process to exit
    try:
        p.wait()
        sys.exit(p.returncode)
    finally:
        terminate_child(p)


if __name__ == '__main__':
    main()
