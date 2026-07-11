import subprocess
import ctypes
import sys
import threading
import socket
import time
import signal


CREATE_NEW_PROCESS_GROUP = 0x00000200


def assign_kill_on_close_job(p):
    """Put the llama child in a wrapper-owned Job Object on Windows."""
    if sys.platform != "win32":
        return None
    try:
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_uint64),
                ("WriteOperationCount", ctypes.c_uint64),
                ("OtherOperationCount", ctypes.c_uint64),
                ("ReadTransferCount", ctypes.c_uint64),
                ("WriteTransferCount", ctypes.c_uint64),
                ("OtherTransferCount", ctypes.c_uint64),
            ]

        class BASIC_LIMITS(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class EXTENDED_LIMITS(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BASIC_LIMITS),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None
        limits = EXTENDED_LIMITS()
        limits.BasicLimitInformation.LimitFlags = 0x2000
        if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            kernel32.CloseHandle(job)
            return None
        if not kernel32.AssignProcessToJobObject(job, wintypes.HANDLE(int(p._handle))):
            kernel32.CloseHandle(job)
            return None
        return job
    except Exception:
        return None


def close_job(job):
    if job and sys.platform == "win32":
        try:
            ctypes.windll.kernel32.CloseHandle(job)
        except Exception:
            pass


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
        try:
            p.wait(timeout=10)
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
    job = assign_kill_on_close_job(p)

    shutting_down = False

    def handle_signal(signum, frame):
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        terminate_child(p)
        sys.exit(0)

    for sig in (
        signal.SIGTERM,
        signal.SIGINT,
        getattr(signal, "SIGHUP", None),
        getattr(signal, "SIGBREAK", None),
    ):
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
        close_job(job)


if __name__ == '__main__':
    main()
