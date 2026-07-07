import subprocess
import sys
from pathlib import Path

from backend.core import registry
from backend.core.config import load_local_config, save_local_config
from backend.llama_args import (
    find_managed_llama_flags,
    format_llama_extra_args,
    is_managed_llama_flag,
    normalize_llama_extra_args,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent
CLI_DIR = BACKEND_DIR.parent


def _runtime_platform_dir() -> str:
    if sys.platform == "win32":
        return "win-x64"
    if sys.platform == "darwin":
        import platform
        arch = "arm64" if platform.machine() == "arm64" else "x64"
        return f"macos-{arch}"
    return "linux-x64"


def _llama_server_path() -> Path:
    name = "llama-server.exe" if sys.platform == "win32" else "llama-server"
    return BACKEND_DIR / "bin" / _runtime_platform_dir() / name


def _current_args() -> list[str]:
    cfg = load_local_config()
    return normalize_llama_extra_args(cfg.get("llama_extra_args", []))


def _save_args(args: list[str]) -> None:
    cfg = load_local_config()
    cfg["llama_extra_args"] = list(args)
    save_local_config(cfg)


def _show_current(args: list[str]) -> None:
    print("\n[llama_set]")
    print(f"  llama_extra_args: {format_llama_extra_args(args)}")
    print("  These unmanaged args are appended after Enchan-managed llama-server flags.")


def _print_static_help() -> None:
    print("\n[llama_set]")
    print("  /llama_set                         Show current unmanaged llama-server args.")
    print("  /llama_set --swa-full              Append unmanaged llama-server args.")
    print("  /llama_set --n-cpu-moe 8           Append a flag and value.")
    print("  /llama_set remove --swa-full       Remove matching token(s).")
    print("  /llama_set clear                   Clear all unmanaged llama-server args.")
    print("  /llama_set help                    Show this help and filtered llama-server flags when available.")
    print("\n[Boundary]")
    print("  Use /set for Enchan-managed settings such as screen_strength, kv_cache_type,")
    print("  context size, samplers, Mirostat, YaRN, model, host/port, mmproj, and reasoning.")
    print("  Use /llama_set only for raw llama.cpp flags Enchan does not manage.")


def _filtered_llama_help(max_lines: int = 160) -> list[str]:
    exe = _llama_server_path()
    if not exe.exists():
        return []
    try:
        completed = subprocess.run(
            [str(exe), "--help"],
            cwd=str(exe.parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
        )
    except Exception:
        return []
    text = (completed.stdout or "") + (completed.stderr or "")
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        tokens = stripped.replace(",", " ").split()
        if any(is_managed_llama_flag(token) for token in tokens):
            continue
        lines.append(line.rstrip())
        if len(lines) >= max_lines:
            lines.append("  ...")
            break
    return lines


@registry.command("/llama_set", desc="Show or change unmanaged llama-server passthrough args.", usage="/llama_set [args|remove args|clear|help]")
def handle_llama_set(
    user_input: str,
    generation_config: dict,
    session_log_path: Path | None = None,
    **kwargs,
) -> tuple[bool, str, bool]:
    file_context = kwargs.get("file_context", "")
    args_obj = kwargs.get("args")
    rest = user_input.strip()[len("/llama_set"):].strip()
    current = _current_args()

    if not rest:
        _show_current(current)
        return True, file_context, False

    lowered = rest.lower()
    if lowered == "help":
        _print_static_help()
        filtered = _filtered_llama_help()
        if filtered:
            print("\n[Unmanaged llama-server flags from bundled --help]")
            for line in filtered:
                print(line)
        else:
            print("\n[Info] Bundled llama-server --help is not available from this checkout.")
        return True, file_context, False

    if lowered in {"clear", "reset"}:
        _save_args([])
        generation_config["llama_extra_args"] = []
        if args_obj is not None:
            args_obj.llama_arg = []
        from backend.enchan_llama_backend import shutdown_enchan_llama
        shutdown_enchan_llama()
        print("[System] llama_extra_args cleared. Enchan engine will restart on the next request.")
        return True, file_context, False

    remove_mode = False
    if lowered.startswith("remove "):
        remove_mode = True
        rest = rest.split(maxsplit=1)[1]

    try:
        requested = normalize_llama_extra_args(rest)
    except ValueError as e:
        print(f"[Error] Could not parse llama args: {e}")
        return True, file_context, False

    if not requested:
        print("[Error] No llama-server args provided.")
        return True, file_context, False

    managed = find_managed_llama_flags(requested)
    if managed:
        names = ", ".join(sorted(set(managed)))
        print(f"[Error] Refusing Enchan-managed llama-server flag(s): {names}")
        print("        Use /set or startup options for managed settings, or /llama_set help for the boundary.")
        return True, file_context, False

    if remove_mode:
        remaining = list(current)
        for token in requested:
            try:
                remaining.remove(token)
            except ValueError:
                pass
        _save_args(remaining)
        generation_config["llama_extra_args"] = remaining
        if args_obj is not None:
            args_obj.llama_arg = remaining
        print(f"[System] llama_extra_args = {format_llama_extra_args(remaining)}")
    else:
        updated = current + requested
        _save_args(updated)
        generation_config["llama_extra_args"] = updated
        if args_obj is not None:
            args_obj.llama_arg = updated
        print(f"[System] llama_extra_args = {format_llama_extra_args(updated)}")

    from backend.enchan_llama_backend import shutdown_enchan_llama
    shutdown_enchan_llama()
    print("[System] Enchan engine will restart with updated llama_extra_args on the next request.")
    return True, file_context, False
