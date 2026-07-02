import os
import sys
import platform
import json
import time
import subprocess
import urllib.error
import urllib.request
import shutil
import socket
import re
import threading
from pathlib import Path
from typing import Optional

# Path Resolution
BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent
def _runtime_platform_dir() -> str:
    if sys.platform == "win32":
        return "win-x64"
    if sys.platform == "darwin":
        arch = "arm64" if platform.machine() == "arm64" else "x64"
        return f"macos-{arch}"
    return "linux-x64"


ENGINE_BIN_DIR = BACKEND_DIR / "bin" / _runtime_platform_dir()
LLAMA_SERVER_NAME = "llama-server.exe" if sys.platform == "win32" else "llama-server"


from session_log import append_session_event

DEFAULT_ENCHAN_LLAMA_PORT = 11435
DEFAULT_ENCHAN_LLAMA_HOST = f"http://localhost:{DEFAULT_ENCHAN_LLAMA_PORT}"

# Store global reference to the running server subprocess and active port
_server_process: Optional[subprocess.Popen] = None
_current_loaded_model: Optional[str] = None
_current_server_port: int = DEFAULT_ENCHAN_LLAMA_PORT
_current_context_size: int = 0
_ram_guard_stop: Optional[threading.Event] = None
_wrapper_port: Optional[int] = None

GIB = 1024 ** 3

_ctrl_handler_ref = None

def _register_ctrl_handler():
    global _ctrl_handler_ref
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes
        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
        def handler(ctrl_type):
            if ctrl_type in (2, 5, 6): # CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT
                if _server_process is not None:
                    # This print won't be seen if terminal is closed, but helps debugging
                    print("\n[System] Terminal closure detected. Gracefully shutting down Enchan Llama...", flush=True)
                    shutdown_enchan_llama()
                return True
            return False
        _ctrl_handler_ref = handler
        ctypes.windll.kernel32.SetConsoleCtrlHandler(_ctrl_handler_ref, True)
    except Exception:
        pass

_register_ctrl_handler()

def get_free_port() -> int:
    """Finds a free port on localhost."""
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def strip_thought_blocks(text: str) -> str:
    """Removes <thought>...</thought> and <think>...</think> blocks to keep multi-turn context clean."""
    if not text:
        return text
    text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


def append_tool_result_event(session_log_path: Path, result: dict, iteration: int, backend: Optional[str] = None):
    event = result.get("event")
    if not isinstance(event, dict):
        return
    payload = dict(event)
    payload["iteration"] = iteration
    if backend:
        payload["backend"] = backend
    append_session_event(session_log_path, payload)


def _format_bytes(n: int) -> str:
    if n >= GIB:
        return f"{n / GIB:.2f} GiB"
    mib = 1024 ** 2
    return f"{n / mib:.0f} MiB"


def get_physical_memory_status() -> tuple[int, int] | None:
    """Returns physical memory as (total_bytes, available_bytes)."""
    if sys.platform == "win32":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys), int(status.ullAvailPhys)
        except Exception:
            return None
    elif sys.platform == "darwin":
        # macOS has no SC_AVPHYS_PAGES; total comes from sysconf and available is
        # derived from vm_stat (free + inactive + speculative pages are reclaimable).
        try:
            page_size = os.sysconf("SC_PAGE_SIZE")
            total = os.sysconf("SC_PHYS_PAGES") * page_size
            out = subprocess.run(
                ["vm_stat"], capture_output=True, text=True, timeout=2
            ).stdout
            avail_pages = 0
            for key in ("Pages free", "Pages inactive", "Pages speculative"):
                match = re.search(rf"{key}:\s+(\d+)\.", out)
                if match:
                    avail_pages += int(match.group(1))
            return int(total), int(avail_pages * page_size)
        except Exception:
            return None
    else:
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            avail_pages = os.sysconf("SC_AVPHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            return int(pages * page_size), int(avail_pages * page_size)
        except Exception:
            return None
    return None


def ram_reserve_bytes(reserve_ratio: float, reserve_gb: float) -> int:
    status = get_physical_memory_status()
    ratio_reserve = 0
    if status is not None:
        ratio_reserve = int(status[0] * max(0.0, reserve_ratio))
    fixed_reserve = int(max(0.0, reserve_gb) * GIB)
    return max(ratio_reserve, fixed_reserve)

def is_server_responding(host: str) -> bool:
    """Checks if the OpenAI-compatible custom server is healthy."""
    try:
        # llama-server exposes a /health endpoint
        url = host.rstrip("/") + "/health"
        with urllib.request.urlopen(url, timeout=1) as resp:
            if resp.status == 200:
                return True
    except Exception:
        pass
    
    # Fallback to checking the models endpoint
    try:
        url = host.rstrip("/") + "/v1/models"
        with urllib.request.urlopen(url, timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False


def _tcp_port_open(port: int, timeout: float = 0.1) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def _kill_process_tree(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/pid", str(pid), "/t", "/f"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        powershell = _powershell_exe()
        if powershell:
            subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-Command",
                    f"Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}' | Invoke-CimMethod -MethodName Terminate",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    else:
        try:
            os.kill(pid, 15)
        except Exception:
            pass


def _wait_for_process_exit(process: subprocess.Popen, timeout: float) -> bool:
    try:
        process.wait(timeout=timeout)
        return True
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return process.poll() is not None


def _wait_for_port_release(port: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _listening_pids_on_port(port):
            return True
        time.sleep(0.2)
    return not _listening_pids_on_port(port)


def _terminate_windows_job(process: subprocess.Popen) -> None:
    if sys.platform != "win32":
        return
    job_handle = getattr(process, "_job_handle", None)
    if not job_handle:
        return
    try:
        import ctypes

        ctypes.windll.kernel32.TerminateJobObject(job_handle, 1)
    except Exception:
        pass


def _powershell_exe() -> Optional[str]:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    bundled = Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if bundled.exists():
        return str(bundled)
    return shutil.which("powershell.exe") or shutil.which("powershell")


def _schedule_windows_cleanup(pid: int, port: int) -> None:
    if sys.platform != "win32":
        return
    powershell = _powershell_exe()
    if not powershell:
        return
    parent_pid = os.getpid()
    command = (
        f"$parent={int(parent_pid)}; $target={int(pid)}; $port={int(port)}; "
        "Wait-Process -Id $parent -Timeout 10 -ErrorAction SilentlyContinue; "
        "Start-Sleep -Milliseconds 500; "
        "Get-CimInstance Win32_Process -Filter \"ProcessId=$target\" | "
        "Invoke-CimMethod -MethodName Terminate -ErrorAction SilentlyContinue; "
        "Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue | "
        "ForEach-Object { "
        "Get-CimInstance Win32_Process -Filter \"ProcessId=$($_.OwningProcess)\" | "
        "Invoke-CimMethod -MethodName Terminate -ErrorAction SilentlyContinue "
        "}"
    )
    try:
        subprocess.Popen(
            [powershell, "-NoProfile", "-Command", command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        pass


def _listening_pids_on_port(port: int) -> set[int]:
    if sys.platform != "win32":
        return set()
    try:
        output = subprocess.check_output(
            ["netstat", "-ano", "-p", "tcp"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return set()

    pids: set[int] = set()
    needle_v4 = f":{port}"
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        local_addr = parts[1]
        state = parts[-2].upper()
        pid_text = parts[-1]
        if state == "LISTENING" and local_addr.endswith(needle_v4):
            try:
                pids.add(int(pid_text))
            except ValueError:
                pass
    return pids


def shutdown_enchan_llama() -> None:
    """Safely terminates the running custom llama-server background process."""
    global _server_process, _current_loaded_model, _current_server_port, _current_context_size, _ram_guard_stop
    shutdown_port = _current_server_port
    shutdown_ok = True

    if _ram_guard_stop is not None:
        _ram_guard_stop.set()
        _ram_guard_stop = None

    if _server_process is not None:
        print("[System] Terminating Enchan Llama background engine...")
        process = _server_process
        process_pid = process.pid

        # Attempt graceful shutdown via wrapper socket first
        if sys.platform == "win32" and _wrapper_port is not None:
            import socket
            try:
                s = socket.socket()
                s.settimeout(2.0)
                s.connect(('127.0.0.1', _wrapper_port))
                s.send(b'stop')
                s.close()
                _wait_for_process_exit(process, timeout=10.0)
            except Exception:
                pass
        elif sys.platform == "win32":
            import signal
            try:
                os.kill(process_pid, signal.CTRL_BREAK_EVENT)
                _wait_for_process_exit(process, timeout=5.0)
            except Exception:
                pass
        else:
            try:
                process.terminate() # SIGTERM on POSIX
                _wait_for_process_exit(process, timeout=5.0)
            except Exception:
                pass

        # Force kill if still running
        if process.poll() is None:
            _terminate_windows_job(process)
            try:
                process.terminate()
            except Exception:
                pass

        if not _wait_for_process_exit(process, timeout=45):
            try:
                _kill_process_tree(process.pid)
            except Exception:
                pass
            for pid in _listening_pids_on_port(shutdown_port):
                try:
                    _kill_process_tree(pid)
                except Exception:
                    pass
            if not _wait_for_process_exit(process, timeout=15):
                shutdown_ok = False

        try:
            job_handle = getattr(process, "_job_handle", None)
            if job_handle:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(job_handle)
        except Exception:
            pass
        _server_process = None

    for pid in _listening_pids_on_port(shutdown_port):
        try:
            _kill_process_tree(pid)
        except Exception:
            pass

    if not _wait_for_port_release(shutdown_port, timeout=30):
        shutdown_ok = False
        if "process_pid" in locals():
            _schedule_windows_cleanup(process_pid, shutdown_port)
            
    _current_loaded_model = None
    _current_server_port = DEFAULT_ENCHAN_LLAMA_PORT
    _current_context_size = 0
    if shutdown_ok:
        print("[System] Engine shut down successfully.")
    else:
        print("[Warning] Engine shutdown requested, but a llama-server process or port is still releasing.")


def get_enchan_llama_context_size() -> int:
    return _current_context_size

def resolve_ollama_model_to_blob(model_name: str) -> tuple[Optional[str], dict]:
    """
    Translates an Ollama model tag (e.g. 'qwen2.5:0.5b') to its actual
    GGUF blob file path inside the standard ~/.ollama/models/blobs directory.
    Also returns the default parameters defined in the model's .params layer.
    """
    # If it is already a direct path to a file, resolve it
    p = Path(model_name)
    if p.exists() and p.is_file():
        return str(p.resolve()), {}

    # Parse namespace and tag
    if ":" in model_name:
        name, tag = model_name.split(":", 1)
    else:
        name, tag = model_name, "latest"

    user_home = Path.home()
    manifests_root = user_home / ".ollama" / "models" / "manifests" / "registry.ollama.ai" / "library"
    blobs_root = user_home / ".ollama" / "models" / "blobs"

    # Standard model path inside 'library/'
    manifest_file = manifests_root / name / tag
    if not manifest_file.exists():
        # Glob alternative directories if there are custom namespaces
        manifest_glob = list(user_home.glob(f".ollama/models/manifests/registry.ollama.ai/*/{name}/{tag}"))
        if manifest_glob:
            manifest_file = manifest_glob[0]
        else:
            return None, {}

    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        
        resolved_blob = None
        params = {}
        
        # Find the layers
        for layer in manifest.get("layers", []):
            digest = layer.get("digest")
            if not digest or not digest.startswith("sha256:"):
                continue
                
            blob_filename = "sha256-" + digest[7:]
            blob_path = blobs_root / blob_filename
            
            media_type = layer.get("mediaType", "")
            if media_type == "application/vnd.ollama.image.model":
                if blob_path.exists():
                    resolved_blob = str(blob_path.resolve())
            elif media_type == "application/vnd.ollama.image.params":
                if blob_path.exists():
                    try:
                        with open(blob_path, "r", encoding="utf-8") as pf:
                            params = json.load(pf)
                    except Exception:
                        pass
                        
        return resolved_blob, params
    except Exception:
        pass

    return None, {}

def _enable_windows_kill_on_exit(process: subprocess.Popen, job_memory_limit_bytes: Optional[int] = None) -> bool:
    """
    On Windows, uses Job Objects to ensure that the spawned child process
    is automatically terminated when this parent process exits or is killed.
    """
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ('ReadOperationCount', ctypes.c_uint64),
                ('WriteOperationCount', ctypes.c_uint64),
                ('OtherOperationCount', ctypes.c_uint64),
                ('ReadTransferCount', ctypes.c_uint64),
                ('WriteTransferCount', ctypes.c_uint64),
                ('OtherTransferCount', ctypes.c_uint64),
            ]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ('PerProcessUserTimeLimit', ctypes.c_uint64),
                ('PerJobUserTimeLimit', ctypes.c_uint64),
                ('LimitFlags', ctypes.c_uint32),
                ('MinimumWorkingSetSize', ctypes.c_void_p),
                ('MaximumWorkingSetSize', ctypes.c_void_p),
                ('ActiveProcessLimit', ctypes.c_uint32),
                ('Affinity', ctypes.c_void_p),
                ('PriorityClass', ctypes.c_uint32),
                ('SchedulingClass', ctypes.c_uint32),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ('BasicLimitInformation', JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ('IoInfo', IO_COUNTERS),
                ('ProcessMemoryLimit', ctypes.c_void_p),
                ('JobMemoryLimit', ctypes.c_void_p),
                ('PeakProcessMemoryUsed', ctypes.c_void_p),
                ('PeakJobMemoryUsed', ctypes.c_void_p),
            ]

        job_handle = kernel32.CreateJobObjectW(None, None)
        if not job_handle:
            return False

        limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        limits.BasicLimitInformation.LimitFlags = 0x2000 # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if job_memory_limit_bytes and job_memory_limit_bytes > 0:
            limits.BasicLimitInformation.LimitFlags |= 0x200 # JOB_OBJECT_LIMIT_JOB_MEMORY
            limits.JobMemoryLimit = ctypes.c_void_p(job_memory_limit_bytes)

        ret = kernel32.SetInformationJobObject(
            job_handle,
            9, # JobObjectExtendedLimitInformation
            ctypes.byref(limits),
            ctypes.sizeof(limits)
        )
        if not ret:
            kernel32.CloseHandle(job_handle)
            return False

        process_handle = wintypes.HANDLE(int(process._handle))
        ret = kernel32.AssignProcessToJobObject(job_handle, process_handle)
        if not ret:
            kernel32.CloseHandle(job_handle)
            return False

        # Keep a reference to job_handle so Windows kills the child when Python exits.
        process._job_handle = job_handle
        return True
    except Exception:
        return False


def _start_ram_guard(
    process: subprocess.Popen,
    reserve_bytes: int,
    action: str = "warn",
    poll_sec: float = 0.25,
) -> threading.Event:
    stop = threading.Event()

    def watch() -> None:
        warned_unavailable = False
        warned_pressure = False
        while not stop.wait(poll_sec):
            if process.poll() is not None:
                return
            status = get_physical_memory_status()
            if status is None:
                if not warned_unavailable:
                    print("[Warning] RAM guard could not read system memory status.")
                    warned_unavailable = True
                continue
            total, available = status
            if available < reserve_bytes:
                message = (
                    f"available={_format_bytes(available)} below reserve={_format_bytes(reserve_bytes)} "
                    f"(total={_format_bytes(total)})."
                )
                if action == "kill":
                    print(f"[Error] RAM guard stopped Enchan Llama: {message}")
                    try:
                        _kill_process_tree(process.pid)
                    except Exception:
                        try:
                            process.kill()
                        except Exception:
                            pass
                    return
                if not warned_pressure:
                    warned_pressure = True
            else:
                warned_pressure = False

    thread = threading.Thread(target=watch, name="enchan-llama-ram-guard", daemon=True)
    thread.start()
    return stop


def _spawn_server_process(cmd: list[str], env: dict[str, str], creationflags: int) -> subprocess.Popen:
    global _wrapper_port
    
    wrapper_port = get_free_port()
    _wrapper_port = wrapper_port
    
    wrapper_script = str(BACKEND_DIR / "enchan_llama_wrapper.py")
    cmd = [sys.executable, wrapper_script, str(wrapper_port)] + cmd
    
    startupinfo = None
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
        startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)

    try:
        return subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            startupinfo=startupinfo,
            cwd=str(ENGINE_BIN_DIR),
        )
    except OSError:
        if sys.platform != "win32":
            raise
        return subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=0,
            cwd=str(ENGINE_BIN_DIR),
        )


def start_enchan_llama_server(
    model_path: str,
    port: int = DEFAULT_ENCHAN_LLAMA_PORT,
    screen_strength: float = 0.3,
    H_c: float = 1.6,
    m: float = 1.5,
    ctx_size: int = 4096,
    gpu_layers: int = -1, # -1 means offload all layers to GPU
    ram_guard: bool = True,
    ram_reserve_ratio: float = 0.2,
    ram_reserve_gb: float = 6.4,
    ram_pressure_action: str = "warn",
    mmap_mode: str = "off",
    fit_mode: bool = True,
    quiet: bool = False,
    text_only: bool = False,
    mtp: bool = False,
    yarn_factor: float = 1.0,
) -> subprocess.Popen:
    """
    Spawns the custom Enchan llama-server runtime in the background
    statically linking with our secure enchan_screening library.
    """
    global _server_process, _current_loaded_model, _current_server_port, _current_context_size, _ram_guard_stop
    host = f"http://localhost:{port}"

    # Resolve Ollama tag to actual GGUF blob path dynamically
    resolved_path, official_params = resolve_ollama_model_to_blob(model_path)
    if resolved_path is None:
        print(f"[Error] Failed to resolve model '{model_path}' to an Ollama blob.")
        print("Please check if the model is installed in your Ollama library (run 'ollama list').")
        return False

    # If the port is busy but we don't own the process (e.g. from an orphaned previous run),
    # robustly kill the orphaned process first so we can start fresh with our new parameters!
    if _server_process is not None and _server_process.poll() is None:
        if _current_loaded_model == model_path and _current_server_port == port:
            return True
        print(f"[System] Swapping engine model from '{_current_loaded_model}' to '{model_path}'...")
        shutdown_enchan_llama()

    if _server_process is None and _tcp_port_open(port):
        print("[System] Cleaning up orphaned llama-server process on our port...")
        for pid in _listening_pids_on_port(port):
            try:
                _kill_process_tree(pid)
            except Exception:
                pass
        shutdown_enchan_llama()
        time.sleep(1.5) # Let OS release the socket

    exe_path = ENGINE_BIN_DIR / LLAMA_SERVER_NAME
    if not exe_path.exists():
        print(f"[Error] Custom Enchan Llama engine not found at: {exe_path}")
        print("Please install or build the Enchan Llama runtime for this platform first.")
        return False

    model_file = Path(resolved_path)
    reserve_bytes = ram_reserve_bytes(ram_reserve_ratio, ram_reserve_gb) if ram_guard else 0
    memory_status = get_physical_memory_status()
    job_memory_limit = None
    if ram_guard and memory_status is not None:
        total_memory, available_memory = memory_status
        if available_memory <= reserve_bytes:
            print(
                "[Error] Refusing to start Enchan Llama: "
                f"available RAM {_format_bytes(available_memory)} is at/below reserve "
                f"{_format_bytes(reserve_bytes)}."
            )
            return False
        if ram_pressure_action == "kill":
            job_memory_limit = max(1, available_memory - reserve_bytes)

    if not quiet:
        print(f"[System] Launching Enchan Llama secure engine (CUDA-Accelerated)...")
        print(f"  * Engine: {exe_path}")
        print(f"  * Model Tag: {model_path}")
        print(f"  * Resolved GGUF Blob: {model_file.resolve()}")
        print(f"  * Config: strength={screen_strength}, H_c={H_c}, m={m}, ctx={ctx_size}")
    if ram_guard and memory_status is not None and not quiet:
        print(
            "  * RAM Guard: "
            f"reserve={_format_bytes(reserve_bytes)}, "
            f"action={ram_pressure_action}, "
            f"child_limit={_format_bytes(job_memory_limit) if job_memory_limit else 'none'}, "
            f"available_now={_format_bytes(memory_status[1])}"
        )
    elif ram_guard and not quiet:
        print("  * RAM Guard: watchdog enabled, preflight memory status unavailable")

    # Build the environment block. Runtime unlock material must be supplied by the caller environment.
    env = os.environ.copy()
    env["LLAMA_ENCHAN_EILM"] = "1"
    env["LLAMA_ENCHAN_EILM_STRENGTH"] = str(screen_strength)
    env["LLAMA_ENCHAN_EILM_DT"] = str(H_c)
    env["LLAMA_ENCHAN_EILM_M"] = str(m)
    env["GGML_CUDA_ENABLE_UNIFIED_MEMORY"] = "1"
    env.pop("GGML_CUDA_NO_PINNED", None)

    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        creationflags |= getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0)
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)

    batch_size = 512
    ubatch_size = 512
    cmd = [
        str(exe_path),
        "-m", str(model_file.resolve()),
        "-c", str(ctx_size),
        "--port", str(port),
        "-ngl", str(gpu_layers),
        "--host", "127.0.0.1",
        "--flash-attn", "auto",
        "--split-mode", "none",
        "--keep", "4",
        "--no-ui",
        "--alias", "enchan-llama",  # Force OpenAI-compatible alias to match payload model name.
        "-b", str(batch_size),
        "-ub", str(ubatch_size),
    ]
    if mmap_mode == "off":
        cmd.append("--no-mmap")
    elif mmap_mode == "on":
        cmd.append("--mmap")
    if fit_mode:
        cmd.extend(["--fit", "on"])

    if mtp:
        # User explicitly requested MTP.
        # Try to pull the optimal draft length from the official parameters if available.
        draft_num = official_params.get("draft_num_predict")
        n_max = str(draft_num) if draft_num else "3"
        cmd.extend(["--spec-type", "draft-mtp", "--spec-draft-n-max", n_max])

    if yarn_factor > 1.0:
        cmd.extend([
            "--rope-scaling", "yarn",
            "--rope-scale", str(yarn_factor),
            "--override-kv", "qwen2.rope.freq_base=float:10000000",
            "--yarn-orig-ctx", "262144"
        ])

    try:
        _server_process = _spawn_server_process(cmd, env, creationflags)
        if not _enable_windows_kill_on_exit(_server_process, job_memory_limit):
            print("[Warning] Could not attach Enchan Llama subprocess to a Windows cleanup job.")
        if ram_guard:
            _ram_guard_stop = _start_ram_guard(_server_process, reserve_bytes, ram_pressure_action)
        _current_server_port = port
    except Exception as e:
        print(f"[Error] Failed to spawn Enchan Llama subprocess: {e}")
        shutdown_enchan_llama()
        return False

    for _ in range(40):
        time.sleep(0.5)
        if is_server_responding(host):
            _current_loaded_model = model_path
            _current_context_size = ctx_size
            if not quiet:
                print(
                    f"[System] Enchan Llama engine is active on {host} "
                    f"(ctx={ctx_size}, batch={batch_size}, ubatch={ubatch_size})"
                )
            return True
        if _server_process.poll() is not None:
            if not quiet:
                print("[Warning] Enchan Llama engine exited during startup.")
            break
    else:
        if not quiet:
            print("[Warning] Timeout waiting for Enchan Llama API to respond.")

    print("[Error] Enchan Llama load failed with requested startup settings.")
    shutdown_enchan_llama()
    return False


def ensure_enchan_llama_running(
    model_path: str,
    screen_strength: float = 0.3,
    H_c: float = 1.6,
    m: float = 1.5,
    ctx_size: int = 4096,
    ram_guard: bool = True,
    ram_reserve_ratio: float = 0.2,
    ram_reserve_gb: float = 6.4,
    ram_pressure_action: str = "warn",
    mmap_mode: str = "off",
    fit_mode: bool = True,
    quiet: bool = False,
    text_only: bool = False,
    mtp: bool = False,
    yarn_factor: float = 1.0,
) -> bool:
    return bool(
        start_enchan_llama_server(
            model_path=model_path,
            screen_strength=screen_strength,
            H_c=H_c,
            m=m,
            ctx_size=ctx_size,
            ram_guard=ram_guard,
            ram_reserve_ratio=ram_reserve_ratio,
            ram_reserve_gb=ram_reserve_gb,
            ram_pressure_action=ram_pressure_action,
            mmap_mode=mmap_mode,
            fit_mode=fit_mode,
            quiet=quiet,
            text_only=text_only,
            mtp=mtp,
            yarn_factor=yarn_factor,
        )
    )


def ensure_enchan_llama_for_request(generation_config: dict | None, args, quiet: bool = True) -> bool:
    model_path = getattr(args, "gguf_model", "") or getattr(args, "ollama_model", "")
    if not model_path:
        print("[Error] No model configured for Enchan Llama.")
        return False
    ok = ensure_enchan_llama_running(
        model_path=model_path,
        screen_strength=getattr(args, "screen_strength", 0.3),
        H_c=getattr(args, "H_c", 1.6),
        m=getattr(args, "m", 1.5),
        ctx_size=int(getattr(args, "ollama_ctx", 4096)),
        ram_guard=not getattr(args, "no_ram_guard", False),
        ram_reserve_ratio=float(getattr(args, "ram_reserve_ratio", 0.05)),
        ram_reserve_gb=float(getattr(args, "ram_reserve_gb", 1.6)),
        ram_pressure_action=getattr(args, "ram_pressure_action", "warn"),
        mmap_mode=getattr(args, "llama_mmap", "off"),
        fit_mode=bool(getattr(args, "llama_fit", False)),
        quiet=quiet,
        text_only=getattr(args, "text_only", False),
        mtp=getattr(args, "mtp", False),
        yarn_factor=float(getattr(args, "yarn_factor", 1.0)),
    )
    runtime_ctx_size = get_enchan_llama_context_size()
    if runtime_ctx_size > 0 and generation_config is not None:
        try:
            args.ollama_ctx = runtime_ctx_size
        except Exception:
            pass
        generation_config["max_input_tokens"] = runtime_ctx_size
    return ok


def generate_enchan_llama_response(
    chat_history: list[dict],
    generation_config: dict,
    session_log_path: Path,
    host: str = DEFAULT_ENCHAN_LLAMA_HOST,
    stream_output: bool = True,
    show_metrics: bool = True,
) -> dict | None:
    """Streams the response from our secure C++ engine using OpenAI-compatible SSE."""
    from ui_theme import get_spinner_status

    api_url = host.rstrip("/") + "/v1/chat/completions"
    
    messages = []
    
    # Prepend the ephemeral system context
    system_context = generation_config.get("system_context")
    if system_context:
        messages.append({
            "role": "system",
            "content": system_context
        })

    for msg in chat_history:
        role = msg.get("role")
        if role in ("assistant", "model"):
            mapped_role = "assistant"
        elif role == "system":
            mapped_role = "system"
        else:
            mapped_role = "user"
            
        messages.append({
            "role": mapped_role,
            "content": msg.get("content", "")
        })

    payload = {
        "model": "enchan-llama",
        "messages": messages,
        "stream": True,
        "timings_per_token": True,
        "temperature": float(generation_config.get("temperature", 1.0)),
        "top_p": float(generation_config.get("top_p", 0.95)),
        "top_k": int(generation_config.get("top_k", 20)),
        "presence_penalty": float(generation_config.get("presence_penalty", 1.5)),
        "max_tokens": int(generation_config.get("max_new_tokens", -1)),
    }
    
    # Qwen3.6 chat_template_kwargs handling
    chat_template_kwargs = {}
    if not generation_config.get("enable_thinking", True):
        chat_template_kwargs["enable_thinking"] = False
    if generation_config.get("preserve_thinking", True):
        chat_template_kwargs["preserve_thinking"] = True
        
    if chat_template_kwargs:
        payload["chat_template_kwargs"] = chat_template_kwargs

    if stream_output and not generation_config.get("suppress_response_header", False):
        width = shutil.get_terminal_size().columns
        model_id = str(generation_config.get("model_id") or "llama")
        if model_id.startswith("enchan:"):
            model_id = model_id[len("enchan:"):]
        if model_id.endswith(".gguf") or "\\" in model_id or "/" in model_id:
            model_id = Path(model_id).stem
        print("\n\x1b[90m" + "-" * width + "\x1b[0m")
        print(f"[Enchan:{model_id}]:\n", end="", flush=True)

    start_time = time.perf_counter()
    content_parts = []
    printed_len = 0
    printed_rendered_len = 0
    think_opt = bool(generation_config.get("think", False)) # deprecated, use view_think
    view_think = bool(generation_config.get("view_think", think_opt))
    content_started = False
    cancelled = False
    final_timings = {}
    status = None
    if stream_output:
        status = get_spinner_status()
        if hasattr(status, "start"):
            status.start()

    reasoning_started = False
    reasoning_ended = False

    def esc_pressed() -> bool:
        if sys.platform != "win32":
            return False
        import msvcrt
        pressed = False
        while msvcrt.kbhit():
            key = msvcrt.getwch()
            if key == "\x1b":
                pressed = True
        return pressed

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw_line in resp:
                if esc_pressed():
                    cancelled = True
                    break
                
                raw_line = raw_line.strip()
                if not raw_line or not raw_line.startswith(b"data: "):
                    continue
                
                data_bytes = raw_line[6:]
                if data_bytes == b"[DONE]":
                    break
                
                try:
                    chunk = json.loads(data_bytes.decode("utf-8"))
                    timings = chunk.get("timings")
                    if isinstance(timings, dict):
                        final_timings = timings
                    delta = chunk["choices"][0].get("delta", {})
                    reasoning = delta.get("reasoning_content", "")
                    content = delta.get("content", "")
                    
                    if reasoning:
                        if not reasoning_started:
                            content_parts.append("<think>\n")
                            reasoning_started = True
                        content_parts.append(reasoning)

                    if content:
                        if reasoning_started and not reasoning_ended:
                            content_parts.append("\n</think>\n")
                            reasoning_ended = True
                        content_parts.append(content)

                    if reasoning or content:
                        if stream_output:
                            content_started = True
                            accumulated = "".join(content_parts)
                            
                            tags = ["<tool_call>", "<thought>", "</thought>", "<think>", "</think>"]
                            max_match = 0
                            for t in tags:
                                for i in range(1, min(len(accumulated), len(t)) + 1):
                                    suffix = accumulated[-i:]
                                    if t.startswith(suffix):
                                        max_match = max(max_match, i)

                            safe_len = len(accumulated) - max_match
                            if safe_len > printed_len:
                                rendered_text = ""
                                temp_in_thought = False
                                temp_in_think = False
                                i = 0
                                while i < safe_len:
                                    if accumulated[i:i+9] == "<thought>":
                                        temp_in_thought = True
                                        if view_think:
                                            rendered_text += "\x1b[3;38;2;120;140;180m<thought>\n" # Italic blue-ish for thought
                                        i += 9
                                    elif accumulated[i:i+10] == "</thought>":
                                        temp_in_thought = False
                                        if view_think:
                                            rendered_text += "\n</thought>\x1b[0m"
                                        i += 10
                                    elif accumulated[i:i+7] == "<think>":
                                        temp_in_think = True
                                        if view_think:
                                            rendered_text += "\x1b[3;38;2;150;150;150m<think>\n" # Italic gray for think
                                        i += 7
                                    elif accumulated[i:i+8] == "</think>":
                                        temp_in_think = False
                                        if view_think:
                                            rendered_text += "\n</think>\x1b[0m"
                                        i += 8
                                    else:
                                        if view_think:
                                            rendered_text += accumulated[i]
                                        elif not temp_in_thought and not temp_in_think:
                                            # If we are NOT viewing thoughts, only render if we are NOT inside a thought block
                                            rendered_text += accumulated[i]
                                        i += 1

                                if len(rendered_text) > printed_rendered_len:
                                    if status is not None:
                                        status.stop()
                                        status = None
                                    print(rendered_text[printed_rendered_len:], end="", flush=True)
                                    printed_rendered_len = len(rendered_text)
                                else:
                                    # If not printed on screen, we are inside a thinking block or raw tag block.
                                    # We dynamically update the spinner label to represent the exact phase!
                                    if status is not None:
                                        from ui_theme import RICH_AVAILABLE
                                        if temp_in_thought:
                                            # Inside <thought> block (local model reasoning)
                                            text_to_show = "Thought... (esc to cancel)"
                                            if RICH_AVAILABLE:
                                                status.update(f"[italic rgb(120,140,180)]{text_to_show}[/]")
                                            else:
                                                status.update(text_to_show)
                                        elif temp_in_think or reasoning_started:
                                            # Inside <think> block (deepseek style reasoning)
                                            text_to_show = "Thinking... (esc to cancel)"
                                            if RICH_AVAILABLE:
                                                status.update(f"[italic rgb(150,150,150)]{text_to_show}[/]")
                                            else:
                                                status.update(text_to_show)
                                printed_len = safe_len
                except Exception:
                    pass

                if esc_pressed():
                    cancelled = True
                    break
    except urllib.error.HTTPError as e:
        if status is not None:
            status.stop()
        body = e.read().decode("utf-8", errors="replace")
        print(f"\n[Error] Enchan Llama HTTP error {e.code}: {body}")
        return None
    except Exception as e:
        if status is not None:
            status.stop()
        print(f"\n[Error] Enchan Llama request failed: {e}")
        return None

    elapsed = time.perf_counter() - start_time
    response = "".join(content_parts)
    if status is not None:
        status.stop()

    if cancelled:
        if stream_output:
            print("\n\x1b[2;90m[System] Enchan Llama generation cancelled by Esc.\x1b[0m")
        return {
            "cancelled": True,
            "response": response,
            "elapsed_sec": elapsed,
        }

    if stream_output:
        print()

    predicted_n = int(final_timings.get("predicted_n") or 0) if final_timings else 0
    predicted_tps = float(final_timings.get("predicted_per_second") or 0.0) if final_timings else 0.0
    prompt_n = int(final_timings.get("prompt_n") or 0) if final_timings else 0
    prompt_tps = float(final_timings.get("prompt_per_second") or 0.0) if final_timings else 0.0
    fallback_tokens_count = len(response) // 4
    tps = predicted_tps if predicted_tps > 0 else (fallback_tokens_count / elapsed if elapsed > 0 else 0)
    if show_metrics and stream_output:
        if predicted_tps > 0:
            print(
                "\x1b[90m"
                f"[Metrics] llama.cpp eval: {predicted_n} tok @ {predicted_tps:.1f} t/s"
                f" | prompt: {prompt_n} tok @ {prompt_tps:.1f} t/s"
                f" | wall: {elapsed:.1f}s"
                "\x1b[0m"
            )
        else:
            print(f"\x1b[90m[Metrics] wall fallback: ~{fallback_tokens_count} chars/4 tok in {elapsed:.1f}s ({tps:.1f} t/s)\x1b[0m")

    return {
        "cancelled": False,
        "response": response,
        "elapsed_sec": elapsed,
        "tps": tps,
        "tokens_count": predicted_n or fallback_tokens_count,
        "timings": final_timings,
        "metrics_source": "llama.cpp" if predicted_tps > 0 else "wall_fallback",
    }

# --- Enchan Llama ReAct Agent Loops ---

def run_enchan_llama_once(
    prompt: str,
    chat_history: list[dict],
    generation_config: dict,
    session_log_path: Path,
    args,
    tokenizer=None,
    plain: bool = False,
    memory_context: str = "",
) -> None:
    from agent_loop import run_agent_loop
    from ollama_backend import build_agent_goal_prompt, format_count, estimate_text_tokens_rough, count_text_tokens
    from session_log import append_session_event

    if not ensure_enchan_llama_for_request(generation_config, args):
        append_session_event(session_log_path, {"type": "error", "stage": "enchan_llama_start"})
        return

    current_prompt = build_agent_goal_prompt(prompt, memory_context)
    chat_history.append({"role": "user", "content": current_prompt})
    input_length = count_text_tokens(tokenizer, current_prompt) if tokenizer is not None else estimate_text_tokens_rough(current_prompt)
    max_input_tokens = int(generation_config["max_input_tokens"])
    if input_length > max_input_tokens:
        chat_history.pop()
        print(f"[Error] Prompt is {format_count(input_length)} tokens, which exceeds limit.")
        return

    append_session_event(
        session_log_path,
        {
            "type": "message",
            "role": "user",
            "display_input": prompt,
            "content": current_prompt,
            "input_tokens_estimate": input_length,
            "backend": "enchan",
            "single_turn": True,
        },
    )

    host = f"http://localhost:{DEFAULT_ENCHAN_LLAMA_PORT}"
    run_agent_loop(
        chat_history=chat_history,
        generation_config=generation_config,
        session_log_path=session_log_path,
        backend="enchan",
        generate_response=lambda: generate_enchan_llama_response(
            chat_history,
            generation_config,
            session_log_path,
            host=host,
            stream_output=not plain,
            show_metrics=not plain,
        ),
        append_tool_result_event=append_tool_result_event,
        tokenizer=tokenizer,
        plain=plain,
        single_turn=True,
        strip_final_thoughts=False,
        print_plain_final=True,
    )


def run_enchan_llama_agent_turn(
    chat_history: list[dict],
    generation_config: dict,
    session_log_path: Path,
    args,
    tokenizer=None,
) -> None:
    from agent_loop import run_agent_loop
    from session_log import append_session_event

    host = f"http://localhost:{DEFAULT_ENCHAN_LLAMA_PORT}"
    if not ensure_enchan_llama_for_request(generation_config, args):
        append_session_event(session_log_path, {"type": "error", "stage": "enchan_llama_start"})
        return

    run_agent_loop(
        chat_history=chat_history,
        generation_config=generation_config,
        session_log_path=session_log_path,
        backend="enchan",
        generate_response=lambda: generate_enchan_llama_response(
            chat_history,
            generation_config,
            session_log_path,
            host=host,
            stream_output=True,
            show_metrics=True,
        ),
        append_tool_result_event=append_tool_result_event,
        tokenizer=tokenizer,
        print_before_action_newline=True,
    )



