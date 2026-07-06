import difflib
import json
import os
import re
import shlex
import shutil
import subprocess
import time
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent

AGENT_MAX_ITERATIONS = 20
DEFAULT_OBSERVATION_MAX_CHARS = 10000

def get_max_obs_chars() -> int:
    try:
        from backend.core.config import load_local_config
        local_cfg = load_local_config()
        return int(local_cfg.get("max_obs_chars", 10000))
    except Exception:
        return 10000
COMPRESSED_DOCUMENT_MAX_CHARS = 24000
READ_DOCUMENT_DEBUG = False

AGENT_SYSTEM_PROMPT = f"""You are Enchan running inside Enchan CLI (workspace root: {Path.cwd()}).

## Capability Philosophy (Freedom & Versatility)
- host_shell is the terminal execution surface. If a command can run in a terminal (git, python, npm, tests, diagnostics, builds), run it directly via host_shell.
- Helper tools are safety and ergonomics lanes. If a helper does not exist, or is insufficient, create or execute custom scripts via the terminal.
- exit_codes and stderr are diagnostic evidence. If you encounter errors, friction, or complex tasks, do not guess. Immediately delegate the context and errors to other available models via delegate_agent or call web_search. If you can run a command, do not ask users to run it.

## Interaction & Decision Loop
- Tool calls are the primary action primitives. If a tool call is executed, wait for the Observation before answering. Do not emit more than one tool call per turn.
- Action First is the execution mandate. If the user requests any file modification, creation, reading, searching, execution, or validation, immediately emit the corresponding tool call (write_text_file, replace_text, search_pattern, or host_shell) first. Do not explain, chat, or make excuses in natural language before executing.
- Verifiable Claims are the truth standard. If the host Observation does not verify an action, do not claim you performed it.
- Language is matched communication. If the user writes in a language (e.g. Japanese), reply in that language. Internal JSON and logs stay in English.
- Tone is plain and professional. If guidelines specify custom titles, use those titles.

## Host Execution & Primitives
- host_shell(command, cwd, shell, timeout_seconds) executes terminal commands with a PowerShell default.
- read_document(path, lines, mode, query) is the file reader.
- search_pattern(regex) is the regex file scanner.
- list_directory(path, depth) is the directory lister.
- replace_text(path, old, new, apply) is the exact text editor. If editing, apply=true.
- write_text_file(path, content, overwrite) is the UTF-8 file writer. If overwriting, overwrite=true.
- apply_patch(patch) is the unified diff patcher.
- git_status(), git_diff(staged, paths), git_add(paths), git_commit(message) are git version controllers.
- web_search(query), list_skills(), use_skill(name, arg), delegate_agent(agent, prompt) are auxiliary tools.

## Workspace & Workflow Rules
- README.md is the project blueprint. If you take actions in any directory, read README.md first to understand the context.
- {CLI_DIR}/memory/guidelines/ and {CLI_DIR}/memory/knowledge/ are the guidelines and knowledge storage. If reusable procedures or guidelines are discovered during conversations with the user, save them to these directories using write_text_file.
- read_document with mode="compress" is the summary extractor. If you read large files to understand the summary, use mode="compress". If you need literal line-by-line checks or pinpoint modifications, specify lines with a narrow range (maximum 150 lines).
- search_pattern on {CLI_DIR}/logs/sessions/*.jsonl is the log-based history retriever. If you need to recall past interactions or decisions, use search_pattern on these files. Do not list_directory on logs/sessions/.
- datetime.now() and log timestamps are the chronologic alignment anchors. Today is {datetime.now().strftime('%Y-%m-%d %A %H:%M local time')}. If you analyze logs or search results, compare the current date with the log 'ts' timestamps to calculate the relative elapsed time and adapt your reasoning.
- Explicit path resolution is the Path Safety rule. If a path is explicit, resolve it directly via resolve_workspace_path. Do not prepend workspace roots or duplicate path segments.
- host_shell with python is the script execution primitive. If you run a Python file, execute it via host_shell. Do not use write_text_file to recreate files.
- Verify → Execute → Verify is the code change policy. If you edit code, validate that it works before editing, and verify again after implementation.
- temp_workspace/ is the temporary file workspace. If writing temporary scripts, patches, or trial files, write them strictly inside temp_workspace/. Keep the memory/ folder pristine.
- Code Change Loop is the version control sequence. If you change code, follow this sequence: inspect -> validate before edits -> edit -> verify after edits (tests/builds/diffs) -> check status/diff -> stage scoped files -> commit ONLY if requested.
"""
NORMAL_MODE_TOOL_GUIDANCE = f"""This chat can use Enchan CLI host runtime automatically. host_shell is the primary open-ended local execution surface; typed helpers exist for safer inspection, editing, Git, and delegation.
If you want every turn to be forced through explicit ReAct tool mode, restart Enchan from PowerShell with:

enchan --agent

Do not claim that shell commands typed inside the chat were executed. Shell launch commands must be run in PowerShell, not inside the model conversation.
When the user asks for local setup or installation, Enchan should use host_shell and typed file tools to diagnose, act, and verify instead of defaulting to manual instructions. If the user reports completing an external step such as restarting the terminal, continue by running the next verification command yourself."""



def truncate_observation(text: str, max_chars: Optional[int] = None) -> str:
    limit = max_chars if max_chars is not None else get_max_obs_chars()
    if len(text) <= limit:
        return text
    
    omitted = len(text) - limit
    warning = (
        f"[SYSTEM TRUNCATION WARNING: The tool output was too large and was truncated. "
        f"Only showing the first {limit} characters. {omitted} characters were omitted from the end. "
        f"If you need to see more, refine your query, specify narrower parameters, or read/execute in segments.]\n"
    )
    # Budget the text
    available_budget = max(500, limit - len(warning))
    return warning + text[:available_budget] + f"\n[truncated {omitted + (limit - available_budget)} chars]"


def resolve_workspace_path(raw_path: str, *, require_file: bool = False, require_inside_cli: bool = False) -> Path:
    path = Path(raw_path.strip("\"'"))
    workspace_root = Path.cwd()
    if not path.is_absolute():
        path = (workspace_root / path).resolve()
    else:
        path = path.resolve()
    if require_inside_cli and path != workspace_root and workspace_root not in path.parents:
        raise ValueError(f"Refusing path outside workspace: {path}")
    if require_file and (not path.exists() or not path.is_file()):
        raise FileNotFoundError(f"File not found: {path}")
    return path


def find_line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, max(0, offset)) + 1


def make_unified_diff(path: Path, before: str, after: str) -> str:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    diff_lines = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=str(path),
        tofile=str(path),
        lineterm="",
    )
    return "\n".join(diff_lines)


def parse_line_range(lines_value) -> tuple[Optional[int], Optional[int]]:
    if lines_value is None or lines_value == "":
        return None, None
    if isinstance(lines_value, int):
        return max(1, lines_value), max(1, lines_value)
    text = str(lines_value).strip()
    if "-" in text:
        left, right = text.split("-", 1)
        start = int(left.strip()) if left.strip() else 1
        end = int(right.strip()) if right.strip() else None
        return max(1, start), end
    value = max(1, int(text))
    return value, value


def tool_read_document(args: dict) -> dict:
    raw_path = args.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return {"ok": False, "error": "read_document requires path."}
    try:
        path = resolve_workspace_path(raw_path, require_file=True)
    except (OSError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    
    with path.open("r", encoding="utf-8", errors="replace") as f:
        content_lines = f.readlines()
        
    total_lines = len(content_lines)
    full_text = "".join(content_lines)
    total_chars = len(full_text)
    
    # Get tokenizer injected by execute_agent_tool, if available
    tokenizer = args.get("__tokenizer")
    model = args.get("__model")
    
    # Precise or CJK-aware token estimation for accurate compression metrics
    if tokenizer is not None:
        try:
            from backend.context_compression import count_text_tokens
            estimated_tokens = count_text_tokens(tokenizer, full_text)
        except Exception:
            estimated_tokens = int(total_chars / 1.5)
    else:
        try:
            from backend.enchan_chat import estimate_text_tokens_rough
            estimated_tokens = estimate_text_tokens_rough(full_text)
        except Exception:
            estimated_tokens = int(total_chars / 1.5)
            
    mode = args.get("mode", "raw")
    if mode == "raw" and estimated_tokens > 5000 and not args.get("lines"):
        mode = "compress"
        args["query"] = args.get("query") or "overall summary, main plot, key events, main characters"
    
    if mode == "compress":
        query = args.get("query", "")
        if not query:
            return {"ok": False, "error": "mode='compress' requires a 'query' argument."}
        
        from backend.reading_agent import execute_reading_pipeline
        import io
        import contextlib
        
        # Capture the stdout from execute_reading_pipeline so the AI sees the exact same metrics
        # as the user (including "story-summary structure preserving" mode, candidates, etc.)
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            compressed, metadata = execute_reading_pipeline(full_text, str(path), query, tokenizer=tokenizer, source_tokens=estimated_tokens, model=model)
            
        metrics_log = captured_output.getvalue().strip()
        if READ_DOCUMENT_DEBUG and metrics_log:
            prefix = f"{path} (Compressed view for query: '{query}')\nSource: {total_chars} chars, ~{estimated_tokens} tokens\n\n{metrics_log}"
        else:
            prefix = f"{path} (Structured compressed view for query: '{query}')\nSource: {total_chars} chars, ~{estimated_tokens} tokens"
        if estimated_tokens > 5000:
            prefix += "\n[WARNING: Large file]"

        if READ_DOCUMENT_DEBUG and metrics_log:
            print(f"\n{metrics_log}")

        return {
            "ok": True,
            "content": truncate_observation(prefix + "\n\n" + compressed, max_chars=COMPRESSED_DOCUMENT_MAX_CHARS),
            "observation_max_chars": COMPRESSED_DOCUMENT_MAX_CHARS,
        }
    try:
        start, end = parse_line_range(args.get("lines"))
    except ValueError as e:
        return {"ok": False, "error": f"Invalid lines value: {e}"}
        
    actual_start = start or 1
    if start is not None:
        end = total_lines if end is None else min(end, total_lines)
        selected = content_lines[start - 1:end]
    else:
        selected = content_lines

    # Construct the body text and the header prefix
    body = "".join(f"{idx}: {line}" for idx, line in enumerate(selected, actual_start))
    actual_end = end or (actual_start + len(selected) - 1)
    prefix = f"{path} lines {actual_start}-{actual_end} of {total_lines} (Total size: {total_chars} chars, ~{estimated_tokens} tokens)"
    if estimated_tokens > 2500 and start is None:
        prefix += "\n[WARNING: Reading full file consumed significant context. Use 'lines' or mode='compress' next time.]"

    full_content = prefix + "\n" + body

    # Strict Halt Check: If reading raw lines exceeds dynamic max chars, return ok=False and demand self-correction!
    limit = get_max_obs_chars()
    if len(full_content) > limit:
        return {
            "ok": False,
            "error": (
                f"Requested raw content (lines {actual_start}-{actual_end}) is too large ({len(full_content)} characters), "
                f"which exceeds the active safety limit of {limit} characters. "
                f"Please request a smaller line window (e.g., maximum 150 lines, such as '{actual_start}-{actual_start + 150}') "
                f"to read in segments, or use mode='compress' with a 'query' to retrieve a smart structured digest. "
                f"[Tip: If your machine has sufficient VRAM/RAM headroom, you or the user can increase this tool safety limit at any time by running the CLI command: /set obs_chars <value> (e.g. /set obs_chars 20000).]"
            )
        }

    return {"ok": True, "content": full_content}


def tool_list_directory(args: dict) -> dict:
    raw_path = args.get("path", "")
    if raw_path is None:
        raw_path = ""
    if not isinstance(raw_path, str):
        return {"ok": False, "error": "list_directory path must be a string."}
    path_text = raw_path.strip("\"'")
    path = CLI_DIR if not path_text else Path(path_text)
    if not path.is_absolute():
        path = (CLI_DIR / path).resolve()
    if not path.exists() or not path.is_dir():
        return {"ok": False, "error": f"Directory not found: {path}"}

    try:
        max_depth = int(args.get("depth", 2))
    except ValueError:
        max_depth = 2

    ignore_dirs = {".git", ".venv", ".venv_cuda", "__pycache__", "node_modules", ".idea", "dist", "build"}
    
    def build_tree(current_path: Path, current_depth: int) -> list[str]:
        lines = []
        if current_depth >= max_depth:
            return lines
            
        try:
            items = sorted(current_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return lines
            
        for item in items:
            indent = "  " * current_depth
            if item.is_dir():
                if item.name in ignore_dirs:
                    try:
                        child_count = sum(1 for _ in item.iterdir())
                        lines.append(f"{indent}📁 {item.name}/ [{child_count} items omitted]")
                    except OSError:
                        lines.append(f"{indent}📁 {item.name}/ [contents omitted]")
                    continue
                lines.append(f"{indent}📁 {item.name}/")
                sub_lines = build_tree(item, current_depth + 1)
                lines.extend(sub_lines)
            else:
                try:
                    size = item.stat().st_size
                    est_tokens = int(size / 3.5)
                    lines.append(f"{indent}📄 {item.name} ({size}B, ~{est_tokens} tokens)")
                except OSError:
                    lines.append(f"{indent}📄 {item.name}")
                    
            if len(lines) >= 200:
                if current_depth == 0:
                    lines.append(f"{indent}... [Tree truncated after 200 items to save context]")
                break
        return lines

    entries = build_tree(path, 0)
    
    content = f"Directory Tree for {path} (Depth: {max_depth}):\n" + ("\n".join(entries) if entries else "[empty or ignored]")
    return {"ok": True, "content": truncate_observation(content)}


def iter_search_files(root: Path):
    ignore_dirs = {".git", ".venv", ".venv_cuda", "__pycache__", "node_modules"}
    ignore_ext = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".webp", ".zip", ".exe", ".dll", ".pyc"}
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for name in files:
            path = Path(current_root) / name
            if path.suffix.lower() in ignore_ext:
                continue
            yield path


def tool_search_pattern(args: dict) -> dict:
    regex = args.get("regex")
    if not isinstance(regex, str) or not regex:
        return {"ok": False, "error": "search_pattern requires regex."}
    try:
        pattern = re.compile(regex)
    except re.error as e:
        return {"ok": False, "error": f"Invalid regex: {e}"}
    matches = []
    for path in iter_search_files(CLI_DIR):
        try:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                for line_no, line in enumerate(f, 1):
                    if pattern.search(line):
                        rel = path.relative_to(CLI_DIR)
                        matches.append(f"{rel}:{line_no}: {line.rstrip()}")
                        if len(matches) >= 80:
                            return {"ok": True, "content": "\n".join(matches) + "\n[truncated after 80 matches]"}
        except Exception:
            continue
    return {"ok": True, "content": "\n".join(matches) if matches else "No matches."}


def tool_replace_text(args: dict) -> dict:
    raw_path = args.get("path")
    old = args.get("old")
    new = args.get("new")
    apply_edit = bool(args.get("apply", False))
    if not isinstance(raw_path, str) or not raw_path.strip():
        return {"ok": False, "error": "replace_text requires path."}
    if not isinstance(old, str) or old == "":
        return {"ok": False, "error": "replace_text requires non-empty old text."}
    if not isinstance(new, str):
        return {"ok": False, "error": "replace_text requires new text."}

    try:
        path = resolve_workspace_path(raw_path, require_file=True, require_inside_cli=True)
    except (OSError, ValueError) as e:
        return {"ok": False, "error": str(e)}

    ignored_ext = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".webp", ".zip", ".exe", ".dll", ".pyc"}
    if path.suffix.lower() in ignored_ext:
        return {"ok": False, "error": f"Refusing binary or non-text file type: {path.suffix}"}

    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            original = f.read()
    except UnicodeDecodeError:
        return {"ok": False, "error": f"File is not valid UTF-8: {path}"}
    except OSError as e:
        return {"ok": False, "error": str(e)}
    if "\x00" in original:
        return {"ok": False, "error": f"Refusing file with NUL bytes: {path}"}

    match_old = old
    match_new = new
    count = original.count(match_old)
    if count == 0 and "\r\n" in original and "\n" in old:
        crlf_old = old.replace("\n", "\r\n")
        crlf_new = new.replace("\n", "\r\n")
        crlf_count = original.count(crlf_old)
        if crlf_count:
            match_old = crlf_old
            match_new = crlf_new
            count = crlf_count

    if count != 1:
        return {
            "ok": False,
            "error": f"replace_text requires old text to match exactly once; found {count} matches in {path}",
        }

    offset = original.index(match_old)
    line_no = find_line_number(original, offset)
    updated = original.replace(match_old, match_new, 1)
    diff = make_unified_diff(path, original, updated)
    event = {
        "type": "edit_applied" if apply_edit else "edit_proposed",
        "tool": "replace_text",
        "path": str(path),
        "line": line_no,
        "old_chars": len(match_old),
        "new_chars": len(match_new),
        "applied": apply_edit,
    }

    if not apply_edit:
        content = (
            f"DRY RUN: replace_text would update {path} at line {line_no}.\n"
            "No file was written. Inspect this diff, then call replace_text with apply=true to apply it.\n\n"
            f"{truncate_observation(diff, max_chars=5000)}"
        )
        return {"ok": True, "content": content, "event": event}

    try:
        with path.open("w", encoding="utf-8", newline="") as f:
            f.write(updated)
    except OSError as e:
        return {"ok": False, "error": str(e)}
    content = (
        f"APPLIED: replace_text updated {path} at line {line_no}.\n"
        "Run verification next, for example: git diff or python -m py_compile.\n\n"
        f"{truncate_observation(diff, max_chars=5000)}"
    )
    return {"ok": True, "content": content, "event": event}


def tool_write_text_file(args: dict) -> dict:
    raw_path = args.get("path")
    content_value = args.get("content")
    overwrite = bool(args.get("overwrite", False))
    if not isinstance(raw_path, str) or not raw_path.strip():
        return {"ok": False, "error": "write_text_file requires path."}
    if not isinstance(content_value, str):
        return {"ok": False, "error": "write_text_file requires string content."}

    try:
        path = resolve_workspace_path(raw_path, require_file=False, require_inside_cli=True)
    except (OSError, ValueError) as e:
        return {"ok": False, "error": str(e)}

    ignored_ext = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".webp", ".zip", ".exe", ".dll", ".pyc"}
    if path.suffix.lower() in ignored_ext:
        return {"ok": False, "error": f"Refusing binary or non-text file type: {path.suffix}"}
    if path.exists() and path.is_dir():
        return {"ok": False, "error": f"Refusing to write over directory: {path}"}
    if path.exists() and not overwrite:
        return {"ok": False, "error": f"File already exists; pass overwrite=true to replace it: {path}"}
    if "\x00" in content_value:
        return {"ok": False, "error": "Refusing content with NUL bytes."}

    existed_before = path.exists()
    before = ""
    if existed_before:
        try:
            before = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return {"ok": False, "error": str(e)}

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content_value, encoding="utf-8", newline="")
    except OSError as e:
        return {"ok": False, "error": str(e)}

    diff = make_unified_diff(path, before, content_value)
    event = {
        "type": "file_written",
        "tool": "write_text_file",
        "path": str(path),
        "chars": len(content_value),
        "overwrite": existed_before,
    }
    action = "overwrote" if existed_before else "created"
    message = (
        f"APPLIED: write_text_file {action} {path} ({len(content_value)} chars).\n"
        "Run verification next, for example: git diff.\n\n"
        f"{truncate_observation(diff, max_chars=5000)}"
    )
    return {"ok": True, "content": message, "event": event}


def _run_git(args: list[str], *, timeout_seconds: int = 60) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", "-C", str(CLI_DIR), "-c", "core.quotePath=false", *args],
        cwd=str(CLI_DIR),
        shell=False,
        capture_output=True,
        timeout=timeout_seconds,
    )
    return completed.returncode, _decode_smart(completed.stdout), _decode_smart(completed.stderr)


def _normalize_git_paths(value) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        parts = [value]
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        parts = value
    else:
        raise ValueError("paths must be a string or list of strings.")
    normalized: list[str] = []
    for item in parts:
        item = item.strip()
        if not item:
            continue
        path = Path(item.strip("\"'"))
        if path.is_absolute():
            path = path.resolve()
            if path != CLI_DIR and CLI_DIR not in path.parents:
                raise ValueError(f"Refusing git path outside workspace: {path}")
            item = str(path.relative_to(CLI_DIR))
        normalized.append(item.replace('\\', '/'))
    return normalized


def _patch_target_paths(patch: str) -> list[Path]:
    paths: list[Path] = []
    for line in patch.splitlines():
        if line.startswith("+++ b/") or line.startswith("--- a/"):
            raw = line[6:].strip()
            if raw == "/dev/null":
                continue
            candidate = (CLI_DIR / raw).resolve()
            if candidate != CLI_DIR and CLI_DIR not in candidate.parents:
                raise ValueError(f"Refusing patch path outside workspace: {candidate}")
            if candidate not in paths:
                paths.append(candidate)
    return paths


def _snapshot_patch_targets(paths: list[Path]) -> dict[Path, bytes | None]:
    snapshot: dict[Path, bytes | None] = {}
    for path in paths:
        snapshot[path] = path.read_bytes() if path.exists() and path.is_file() else None
    return snapshot


def _patch_targets_changed(before: dict[Path, bytes | None]) -> bool:
    for path, old_content in before.items():
        new_content = path.read_bytes() if path.exists() and path.is_file() else None
        if new_content != old_content:
            return True
    return False

def _parse_hunk_header(header: str) -> tuple[int, int, int, int]:
    match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", header)
    if not match:
        raise ValueError(f"Invalid hunk header: {header}")
    old_start = int(match.group(1))
    old_count = int(match.group(2) or "1")
    new_start = int(match.group(3))
    new_count = int(match.group(4) or "1")
    return old_start, old_count, new_start, new_count


def _line_body(line: str) -> str:
    return line[1:] if line else ""


def _old_line_text(line: str) -> str:
    return line.rstrip("\r\n")


def _apply_unified_patch_to_file(path: Path, hunks: list[list[str]], *, new_file: bool, delete_file: bool) -> bytes | None:
    old_lines = [] if new_file or not path.exists() else path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    old_index = 0
    output: list[str] = []
    for hunk in hunks:
        if not hunk:
            continue
        old_start, _old_count, _new_start, _new_count = _parse_hunk_header(hunk[0])
        hunk_old_index = max(old_start - 1, 0)
        if hunk_old_index < old_index:
            raise ValueError(f"Overlapping hunk for {path}")
        output.extend(old_lines[old_index:hunk_old_index])
        old_index = hunk_old_index
        for line in hunk[1:]:
            if not line:
                continue
            marker = line[0]
            body = _line_body(line)
            if marker == " ":
                if old_index >= len(old_lines) or _old_line_text(old_lines[old_index]) != body:
                    raise ValueError(f"Patch context mismatch in {path}: {body}")
                output.append(old_lines[old_index])
                old_index += 1
            elif marker == "-":
                if old_index >= len(old_lines) or _old_line_text(old_lines[old_index]) != body:
                    raise ValueError(f"Patch removal mismatch in {path}: {body}")
                old_index += 1
            elif marker == "+":
                output.append(body + "\n")
            elif marker == '\\':
                continue
            else:
                raise ValueError(f"Invalid patch line marker {marker!r} in {path}")
    output.extend(old_lines[old_index:])
    if delete_file:
        return None
    return "".join(output).encode("utf-8")


def _parse_unified_patch(patch: str) -> list[dict]:
    lines = patch.splitlines()
    files: list[dict] = []
    i = 0
    while i < len(lines):
        if not lines[i].startswith("diff --git "):
            i += 1
            continue
        old_path = None
        new_path = None
        hunks: list[list[str]] = []
        i += 1
        while i < len(lines) and not lines[i].startswith("diff --git "):
            line = lines[i]
            if line.startswith("--- "):
                old_path = line[4:].strip()
            elif line.startswith("+++ "):
                new_path = line[4:].strip()
            elif line.startswith("@@ "):
                hunk = [line]
                i += 1
                while i < len(lines) and not lines[i].startswith("@@ ") and not lines[i].startswith("diff --git "):
                    hunk.append(lines[i])
                    i += 1
                hunks.append(hunk)
                continue
            i += 1
        if old_path is None or new_path is None or not hunks:
            raise ValueError("Patch must include ---/+++ paths and at least one hunk.")
        target_raw = new_path if new_path != "/dev/null" else old_path
        if target_raw.startswith("a/") or target_raw.startswith("b/"):
            target_raw = target_raw[2:]
        target = (CLI_DIR / target_raw).resolve()
        if target != CLI_DIR and CLI_DIR not in target.parents:
            raise ValueError(f"Refusing patch path outside workspace: {target}")
        files.append({
            "path": target,
            "hunks": hunks,
            "new_file": old_path == "/dev/null",
            "delete_file": new_path == "/dev/null",
        })
    if not files:
        raise ValueError("No diff --git file patches found.")
    return files


def tool_apply_patch(args: dict) -> dict:
    patch = args.get("patch")
    if not isinstance(patch, str) or not patch.strip():
        return {"ok": False, "error": "apply_patch requires patch."}
    patch = patch.replace("\r\n", "\n")
    if "\x00" in patch:
        return {"ok": False, "error": "Refusing patch with NUL bytes."}
    try:
        file_patches = _parse_unified_patch(patch)
        before_targets = _snapshot_patch_targets([item["path"] for item in file_patches])
        updates: list[tuple[Path, bytes | None]] = []
        for item in file_patches:
            updates.append((item["path"], _apply_unified_patch_to_file(
                item["path"],
                item["hunks"],
                new_file=bool(item["new_file"]),
                delete_file=bool(item["delete_file"]),
            )))
        for path, content in updates:
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        if not _patch_targets_changed(before_targets):
            return {"ok": False, "error": "Patch parsed successfully but target files did not change."}
        return {
            "ok": True,
            "content": "APPLIED: apply_patch updated the workspace. Run verification next, for example git diff or py_compile.",
            "event": {"type": "edit_applied", "tool": "apply_patch", "chars": len(patch), "applied": True},
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_git_status(args: dict) -> dict:
    code, stdout_str, stderr_str = _run_git(["status", "--short", "--", "."], timeout_seconds=30)
    content = f"exit_code: {code}\nstdout:\n{stdout_str}\nstderr:\n{stderr_str}"
    return {"ok": code == 0, "content": content}


def tool_git_diff(args: dict) -> dict:
    cmd = ["diff"]
    if bool(args.get("staged", False)):
        cmd.append("--cached")
    paths = _normalize_git_paths(args.get("paths"))
    cmd.append("--")
    if paths:
        cmd.extend(paths)
    else:
        cmd.append(".")
    code, stdout_str, stderr_str = _run_git(cmd, timeout_seconds=60)
    content = f"exit_code: {code}\nstdout:\n{stdout_str}\nstderr:\n{stderr_str}"
    return {"ok": code == 0, "content": truncate_observation(content, max_chars=20000), "observation_max_chars": 20000}


def tool_git_add(args: dict) -> dict:
    paths = _normalize_git_paths(args.get("paths"))
    if not paths:
        return {"ok": False, "error": "git_add requires paths."}
    code, stdout_str, stderr_str = _run_git(["add", "--", *paths], timeout_seconds=60)
    content = f"paths: {paths}\nexit_code: {code}\nstdout:\n{stdout_str}\nstderr:\n{stderr_str}"
    return {"ok": code == 0, "content": content}


def tool_git_commit(args: dict) -> dict:
    message = args.get("message")
    if not isinstance(message, str) or not message.strip():
        return {"ok": False, "error": "git_commit requires message."}
    message = message.strip()
    code, stdout_str, stderr_str = _run_git(["commit", "-m", message], timeout_seconds=120)
    content = f"message: {message}\nexit_code: {code}\nstdout:\n{stdout_str}\nstderr:\n{stderr_str}"
    return {"ok": code == 0, "content": content}

def _resolve_command_cwd(args: dict) -> Path:
    cwd_value = args.get("cwd")
    cwd = CLI_DIR
    if isinstance(cwd_value, str) and cwd_value.strip():
        candidate = Path(cwd_value.strip("\"'"))
        if not candidate.is_absolute():
            candidate = (CLI_DIR / candidate).resolve()
        if not candidate.exists() or not candidate.is_dir():
            raise FileNotFoundError(f"Working directory not found: {candidate}")
        cwd = candidate
    return cwd


def _host_shell_argv(command: str, shell_name: str) -> tuple[list[str], str]:
    shell_name = (shell_name or "powershell").strip().lower()
    if shell_name in {"powershell", "pwsh", "ps"}:
        exe = shutil.which("pwsh") or shutil.which("powershell") or "powershell"
        preamble = "[Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $OutputEncoding = [Console]::OutputEncoding; "
        return [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", preamble + command], "powershell"
    if shell_name in {"cmd", "cmd.exe"}:
        return ["cmd.exe", "/d", "/s", "/c", command], "cmd"
    if shell_name in {"sh", "bash"}:
        return [shell_name, "-lc", command], shell_name
    raise ValueError("host_shell shell must be powershell, cmd, sh, or bash.")


def tool_host_shell(args: dict) -> dict:
    command = args.get("command") or args.get("cmd")
    if not isinstance(command, str) or not command.strip():
        return {"ok": False, "error": "host_shell requires command."}
    command = command.strip()
    if command.lower() == "pwd":
        command = "Get-Location"
    try:
        cwd = _resolve_command_cwd(args)
        timeout_seconds = max(1, min(int(args.get("timeout_seconds", 30) or 30), 300))
        max_output_chars = max(
            1000,
            min(int(args.get("max_output_chars", get_max_obs_chars()) or get_max_obs_chars()), 500000),
        )
        argv, shell_name = _host_shell_argv(command, str(args.get("shell") or "powershell"))
        started = time.perf_counter()
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            shell=False,
            capture_output=True,
            timeout=timeout_seconds,
        )
        elapsed = time.perf_counter() - started
        stdout_str = _decode_smart(completed.stdout)
        stderr_str = _decode_smart(completed.stderr)
        content = (
            f"tool: host_shell\n"
            f"shell: {shell_name}\n"
            f"cwd: {cwd}\n"
            f"command: {command}\n"
            f"timeout_seconds: {timeout_seconds}\n"
            f"duration_seconds: {elapsed:.3f}\n"
            f"exit_code: {completed.returncode}\n"
            f"stdout:\n{stdout_str}\n"
            f"stderr:\n{stderr_str}"
        )
        return {"ok": completed.returncode == 0, "content": truncate_observation(content, max_chars=max_output_chars)}
    except subprocess.TimeoutExpired as e:
        return {"ok": False, "error": f"host_shell command timed out after {e.timeout} seconds."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_execute_command(args: dict) -> dict:
    if "command" not in args and "cmd" in args:
        args = dict(args)
        args["command"] = args["cmd"]
    return tool_host_shell(args)


def tool_web_search(args: dict) -> dict:
    from backend.web_search_service import perform_web_search
    query = args.get("query", "")
    if not query:
        return {"ok": False, "error": "web_search requires a 'query' argument."}
    results = perform_web_search(query)
    if not results:
        content = "No results found."
    elif len(results) == 1 and "error" in results[0]:
        content = f"Error: {results[0]['error']}"
    else:
        lines = []
        for r in results:
            if "error" in r:
                lines.append(f"Error: {r['error']}")
            else:
                lines.append(f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}\n")
        content = "\n".join(lines)
    return {"ok": True, "content": content}


def tool_list_skills(args: dict) -> dict:
    from backend.skills_loader import list_registered_skills
    content = list_registered_skills()
    return {"ok": True, "content": content}


def tool_use_skill(args: dict) -> dict:
    skill_name = args.get("skill_name") or args.get("name")
    argument = args.get("argument") or args.get("value") or ""
    method = args.get("method") or "invoke"
    params = args.get("params") if isinstance(args.get("params"), dict) else None
    if not skill_name:
        return {"ok": False, "error": "use_skill requires 'skill_name'."}
    if params is None and not argument:
        return {"ok": False, "error": "use_skill requires either 'params' for a typed method or an 'argument' string."}
    from contextlib import redirect_stderr, redirect_stdout
    from backend.skills_loader import run_skill
    from backend.ui_theme import stream_agent_observation

    stream = stream_agent_observation("use_skill")
    ok = True
    content = ""
    try:
        with redirect_stdout(stream), redirect_stderr(stream):
            content = run_skill(str(skill_name), str(argument), method=str(method), params=params)
        returned_content = str(content or "").strip()
        if returned_content and returned_content not in stream.getvalue():
            stream.write(("\n" if stream.getvalue().strip() else "") + returned_content + "\n")
    except Exception as e:
        ok = False
        content = f"Error while running skill '{skill_name}': {e}"
        stream.write(content + "\n")
    finally:
        stream.close()

    captured_output = stream.getvalue().strip()
    returned_content = str(content or "").strip()
    if captured_output:
        if returned_content and returned_content not in captured_output:
            content = f"{captured_output}\n\n{returned_content}"
        else:
            content = captured_output
    return {"ok": ok, "content": content, "displayed": True}

def _load_local_config() -> dict:
    config_path = CLI_DIR / "enchan_config.json"
    if not config_path.exists():
        return {}
    try:
        with config_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _command_parts(value, default: list[str]) -> list[str]:
    if isinstance(value, list) and all(isinstance(part, str) for part in value):
        return [part for part in value if part]
    if isinstance(value, str) and value.strip():
        return shlex.split(value, posix=False)
    return list(default)


def _decode_smart(b: bytes) -> str:
    if not b:
        return ""
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("cp932", errors="replace")


def tool_delegate_agent(args: dict) -> dict:
    agent = str(args.get("agent", "")).strip().lower()
    prompt = args.get("prompt") or args.get("argument") or args.get("value") or ""
    if agent not in {"codex", "gemini", "claude"}:
        return {"ok": False, "error": "delegate_agent requires agent='codex', 'gemini', or 'claude'."}
    if not isinstance(prompt, str) or not prompt.strip():
        return {"ok": False, "error": "delegate_agent requires a non-empty prompt."}

    local_cfg = _load_local_config()
    default_commands = {
        "codex": ["codex", "exec"],
        "gemini": ["gemini", "--model", "gemini-3.5-flash", "--prompt"],
        "claude": ["claude"],
    }
    command = _command_parts(local_cfg.get(f"{agent}_command"), default_commands[agent])
    if not command:
        return {"ok": False, "error": f"No command configured for {agent}."}

    executable = shutil.which(command[0])
    if executable is None:
        return {
            "ok": False,
            "error": (
                f"External agent command not found on PATH: {command[0]}. "
                f"Set '{agent}_command' in enchan_config.json if this machine uses a different launcher."
            ),
        }

    timeout = int(local_cfg.get(f"{agent}_timeout_seconds", local_cfg.get("delegate_timeout_seconds", 600)))
    run_args = command + [prompt.strip()]
    try:
        completed = subprocess.run(
            run_args,
            cwd=str(CLI_DIR),
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        return {"ok": False, "error": f"{agent} delegation timed out after {e.timeout} seconds."}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    stdout_str = _decode_smart(completed.stdout)
    stderr_str = _decode_smart(completed.stderr)
    content = (
        f"agent: {agent}\n"
        f"cwd: {CLI_DIR}\n"
        f"command: {' '.join(command)} [prompt]\n"
        f"exit_code: {completed.returncode}\n"
        f"stdout:\n{stdout_str}\n"
        f"stderr:\n{stderr_str}"
    )
    return {"ok": completed.returncode == 0, "content": truncate_observation(content, max_chars=12000)}

TOOL_REGISTRY = {
    "list_directory": tool_list_directory,
    "read_document": tool_read_document,
    "search_pattern": tool_search_pattern,
    "replace_text": tool_replace_text,
    "write_text_file": tool_write_text_file,
    "write_document": tool_write_text_file,
    "apply_patch": tool_apply_patch,
    "host_shell": tool_host_shell,
    "execute_command": tool_execute_command,
    "web_search": tool_web_search,
    "list_skills": tool_list_skills,
    "use_skill": tool_use_skill,
    "delegate_agent": tool_delegate_agent,
    "git_status": tool_git_status,
    "git_diff": tool_git_diff,
    "git_add": tool_git_add,
    "git_commit": tool_git_commit,
}


def _interactive_security_prompt() -> bool:
    from backend.ui_theme import interactive_yes_no

    return interactive_yes_no("Allow execution?", default_yes=True)



def _tool_requires_permission(tool_name: str, args: dict) -> bool:
    if tool_name in ("host_shell", "execute_command"):
        return False
    if tool_name in ("write_text_file", "write_document", "apply_patch", "use_skill", "git_add", "git_commit"):
        return True
    if tool_name == "replace_text":
        apply_val = args.get("apply", False)
        return str(apply_val).lower() == "true" or apply_val is True
    return False

def execute_agent_tool(call: dict, tokenizer=None, model=None) -> dict:
    tool_name = call.get("tool")
    if tool_name == "_parse_error":
        return {"tool": tool_name, "ok": False, "observation": call.get("error", "Invalid tool call.")}
    tool = TOOL_REGISTRY.get(tool_name)
    if tool is None:
        return {"tool": tool_name, "ok": False, "observation": f"Unknown tool: {tool_name}"}
    
    args = call.get("args", {})

    # --- Security Confirmation for Local Actions ---
    # We require explicit user permission before Enchan CLI performs local modifications.
    # We explicitly EXCLUDE 'delegate_agent' because external agents (Gemini/Codex) 
    # already have their own robust built-in security prompts.
    requires_permission = _tool_requires_permission(tool_name, args)
    if requires_permission:
        print(f"\n\x1b[38;2;190;170;120m⚠️  [Security Request]\x1b[0m \x1b[38;2;210;200;200mThe local Enchan AI wants to perform a sensitive action:\x1b[0m")
        print(f"  \x1b[38;2;210;200;200mTool: {tool_name}\x1b[0m")
        if tool_name in ("host_shell", "execute_command"):
            print(f"  \x1b[38;2;210;200;200mCommand: {args.get('command') or args.get('cmd')}\x1b[0m")
        elif tool_name in ("write_text_file", "write_document"):
            print(f"  \x1b[38;2;210;200;200mTarget: {args.get('path')}\x1b[0m")
        elif tool_name == "apply_patch":
            print(f"  \x1b[38;2;210;200;200mPatch chars: {len(str(args.get('patch') or ''))}\x1b[0m")
        elif tool_name in ("git_add", "git_commit"):
            print(f"  \x1b[38;2;210;200;200mGit args: {args}\x1b[0m")
        elif tool_name == "replace_text":
            print(f"  \x1b[38;2;210;200;200mTarget: {args.get('path')} (apply=True)\x1b[0m")
        elif tool_name == "use_skill":
            target = args.get('skill_name') or 'unknown'
            print(f"  \x1b[38;2;210;200;200mSkill: {target}\x1b[0m")
            
        allow = _interactive_security_prompt()
        
        if not allow:
            print("\x1b[38;2;180;100;100m  [System] Execution denied by user.\x1b[0m")
            return {
                "tool": tool_name, 
                "ok": False, 
                "observation": "User denied permission to execute this tool. You must ask the user for further instructions or find a safe alternative approach."
            }

    if tokenizer is not None:
        args["__tokenizer"] = tokenizer
    if model is not None:
        args["__model"] = model
        
    result = tool(args)
    observation = result.get("content") or result.get("error")
    response = {"tool": tool_name, "ok": bool(result.get("ok")), "observation": observation or ""}
    if isinstance(result.get("observation_max_chars"), int):
        response["observation_max_chars"] = result["observation_max_chars"]
    if isinstance(result.get("event"), dict):
        response["event"] = result["event"]
    if result.get("displayed"):
        response["displayed"] = True
    return response
