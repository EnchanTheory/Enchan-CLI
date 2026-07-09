import re
import sys
import subprocess
from pathlib import Path
from backend.session_log import append_session_event
from backend.ui_theme import print_python_execution, print_python_timeout

BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent

PYTHON_EXECUTION_HINT_RE = re.compile(
    r"(実行|走らせ|動かし|叩い|試し|run|execute|launch)",
    re.IGNORECASE,
)


def wants_python_file_execution(query: str) -> bool:
    return bool(query and PYTHON_EXECUTION_HINT_RE.search(query))


def truncate_observation(text: str, max_chars: int = 12000) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + f"\n\n... [TRUNCATED {len(text) - max_chars} CHARS] ...\n\n" + text[-half:]


def decode_smart(data) -> str:
    if isinstance(data, str):
        return data
    if not data:
        return ""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp932", errors="replace")


def run_python_file_from_prompt(
    script_path: Path,
    query: str,
    session_log_path: Path,
    timeout_sec: int = 120,
) -> None:
    root = CLI_DIR.resolve()
    resolved_script = script_path.resolve()
    if resolved_script != root and root not in resolved_script.parents:
        print(f"[Error] Refusing to execute Python outside CLI root: {resolved_script}")
        append_session_event(
            session_log_path,
            {
                "type": "python_file_execution_refused",
                "path": str(resolved_script),
                "reason": "outside_cli_root",
            },
        )
        return

    cmd = [sys.executable, str(resolved_script)]
    append_session_event(
        session_log_path,
        {
            "type": "python_file_execution_started",
            "path": str(resolved_script),
            "query": query,
            "cmd": cmd,
            "timeout_sec": timeout_sec,
        },
    )
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(resolved_script.parent),
            capture_output=True,
            timeout=timeout_sec,
        )

        stdout = decode_smart(completed.stdout)
        stderr = decode_smart(completed.stderr)
        display_stdout = truncate_observation(stdout, max_chars=12000)
        display_stderr = truncate_observation(stderr, max_chars=12000)

        print_python_execution(completed.returncode, display_stdout, display_stderr)
        append_session_event(
            session_log_path,
            {
                "type": "python_file_execution_finished",
                "path": str(resolved_script),
                "returncode": completed.returncode,
                "stdout": display_stdout,
                "stderr": display_stderr,
            },
        )
    except subprocess.TimeoutExpired as e:
        stdout = decode_smart(e.stdout)
        stderr = decode_smart(e.stderr)
        display_stdout = truncate_observation(stdout, max_chars=12000)
        display_stderr = truncate_observation(stderr, max_chars=12000)

        print_python_timeout(timeout_sec, display_stdout, display_stderr)
        append_session_event(
            session_log_path,
            {
                "type": "python_file_execution_timeout",
                "path": str(resolved_script),
                "timeout_sec": timeout_sec,
                "stdout": display_stdout,
                "stderr": display_stderr,
            },
        )
    except Exception as e:
        print(f"[Error] Python execution failed: {e}")
        append_session_event(
            session_log_path,
            {
                "type": "python_file_execution_error",
                "path": str(resolved_script),
                "message": str(e),
            },
        )
