from pathlib import Path

from backend.core import registry
from backend.core.config import load_local_config, save_local_config
from backend.llama_args import (
    find_managed_llama_flags,
    format_llama_extra_args,
    normalize_llama_extra_args,
)

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
    print("  Reference: https://github.com/ggml-org/llama.cpp/blob/master/tools/cli/README.md")



@registry.command("/llama_set", desc="Show or change unmanaged llama-server passthrough args.", usage="/llama_set [args|reset]")
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
        from backend.ui_theme import styled_input
        print()
        change_input = styled_input("Select parameter and value to change (e.g. '--n-cpu-moe 8', 'reset', or Enter to cancel): ")
        if not change_input:
            print("[System] No changes made.")
            return True, file_context, False
        rest = change_input.strip()

    lowered = rest.lower()

    if lowered == "reset":
        _save_args([])
        generation_config["llama_extra_args"] = []
        if args_obj is not None:
            args_obj.llama_arg = []
        from backend.enchan_llama_backend import shutdown_enchan_llama
        shutdown_enchan_llama()
        print("[System] llama_extra_args cleared. Enchan engine will restart on the next request.")
        return True, file_context, False

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
        print("[Error] One or more specified flags are managed by Enchan and cannot be set here.")
        print("        Use /set or startup options for managed settings.")
        return True, file_context, False

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
