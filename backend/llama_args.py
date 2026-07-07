import os
import shlex
from typing import Iterable

MANAGED_LLAMA_FLAGS = {
    "-m",
    "--model",
    "-c",
    "--ctx-size",
    "--port",
    "--host",
    "-ngl",
    "--n-gpu-layers",
    "--flash-attn",
    "--split-mode",
    "--keep",
    "--no-ui",
    "--alias",
    "-b",
    "--batch-size",
    "-ub",
    "--ubatch-size",
    "--mmproj",
    "-lcd",
    "--lookup-cache-dynamic",
    "--dynatemp-range",
    "--mirostat",
    "--mirostat-lr",
    "--mirostat-ent",
    "--no-mmap",
    "--mmap",
    "--fit",
    "--rope-scaling",
    "--rope-scale",
    "--yarn-orig-ctx",
    "--cache-type-k",
    "--cache-type-v",
    "-ctk",
    "-ctv",
    "--reasoning",
    "--reasoning-format",
    "--reasoning-budget",
    "--reasoning-preserve",
    "--no-reasoning-preserve",
}

MANAGED_LLAMA_FLAG_PREFIXES = (
    "--mirostat-",
    "--dynatemp-",
    "--rope-",
    "--yarn-",
    "--cache-type-",
    "--reasoning-",
)


def _strip_outer_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def normalize_llama_extra_args(values: Iterable[str] | str | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    args: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        args.extend(_strip_outer_quotes(arg) for arg in shlex.split(text, posix=(os.name != "nt")))
    return args


def llama_arg_flag_name(token: str) -> str:
    if not token.startswith("-"):
        return ""
    return token.split("=", 1)[0]


def is_managed_llama_flag(token: str) -> bool:
    flag = llama_arg_flag_name(token)
    if not flag:
        return False
    if flag in MANAGED_LLAMA_FLAGS:
        return True
    return any(flag.startswith(prefix) for prefix in MANAGED_LLAMA_FLAG_PREFIXES)


def find_managed_llama_flags(args: Iterable[str]) -> list[str]:
    found: list[str] = []
    for token in args:
        if is_managed_llama_flag(str(token)):
            found.append(llama_arg_flag_name(str(token)))
    return found


def format_llama_extra_args(args: Iterable[str]) -> str:
    values = [str(arg) for arg in args]
    if not values:
        return "(none)"
    return " ".join(shlex.quote(value) for value in values)
