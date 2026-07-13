import difflib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent

AGENT_MAX_ITERATIONS = 20
DEFAULT_OBSERVATION_MAX_CHARS = 10000
DEFAULT_HOST_SHELL = "powershell" if os.name == "nt" else "sh"
DEFAULT_HOST_SHELL_DESCRIPTION = "PowerShell on Windows, sh on macOS/Linux"
COMPRESSED_DOCUMENT_MAX_CHARS = 24000
READ_DOCUMENT_DEBUG = False


def get_max_obs_chars() -> int:
    try:
        from backend.core.config import load_local_config
        return int(load_local_config().get("max_obs_chars", 10000))
    except Exception:
        return 10000


AGENT_SYSTEM_PROMPT = f"""You are Enchan running inside Enchan CLI (workspace root: {Path.cwd()}).

## Capability Philosophy (Freedom & Versatility)
- run_command is the terminal execution surface. If a command can run in a terminal (git, python, npm, tests, diagnostics, builds), run it directly via run_command.
- Helper tools are safety and ergonomics lanes. If a helper does not exist, or is insufficient, create or execute custom scripts via the terminal.
- exit_codes and stderr are diagnostic evidence. If you encounter errors, friction, or complex tasks, do not guess. Immediately delegate the context and errors to other available models via delegate_agent or call web_search. If you can run a command, do not ask users to run it.

## Interaction & Decision Loop
- Tool calls are the primary action primitives. If a tool call is executed, wait for the Observation before answering. Do not emit more than one tool call per turn.
- Action First is the execution mandate. If the user requests any file modification, creation, reading, searching, execution, or validation, immediately emit the corresponding tool call first.
- Verifiable Claims are the truth standard. If the host Observation does not verify an action, do not claim you performed it.
- Visible Response Contract: never expose private reasoning, planning, or analysis in normal message content.
- Simple Conversation Rule: for greetings, thanks, acknowledgements, or small talk, do not use tools and reply directly.
- Language is matched communication. If the user writes in Japanese, reply in Japanese.

## Host Execution & Primitives
- search_code(query, regex, path, context_lines, max_results, mode) is the primary code search tool. It prefers rg when available and supports mode="compress" for large search digests.
- read_file(path, lines, mode, query) is the primary file reader. Use mode="compress" for large documents or structured extraction.
- edit_file(path, patch, old, new, content, overwrite, apply) is the single editing surface for patch, exact replace, and write operations.
- run_command(command, cwd, shell, timeout_seconds) executes terminal commands with the OS-native default shell ({DEFAULT_HOST_SHELL_DESCRIPTION}).
- web_browse, web_search, list_skills, use_skill, and delegate_agent are unique capabilities and remain reachable.

## Workspace & Workflow Rules
- README.md is the project blueprint. If you take actions in any directory, read README.md first to understand the context.
- {CLI_DIR}/memory/guidelines/ and {CLI_DIR}/memory/knowledge/ are the guidelines and knowledge storage.
- read_file with mode="compress" is the summary extractor. If you read large files to understand the summary, use mode="compress".
- datetime.now() and log timestamps are the chronologic alignment anchors.
- run_command with python is the script execution primitive.
- Verify -> Execute -> Verify is the code change policy.
"""


def get_agent_system_prompt() -> str:
    try:
        from backend.skills_loader import render_skill_catalog_for_prompt
        skill_catalog = render_skill_catalog_for_prompt()
    except Exception as e:
        skill_catalog = f"Skill catalog unavailable: {e}"
    current_datetime = datetime.now().astimezone().strftime("%Y-%m-%d %A %H:%M:%S %Z")
    return f"{AGENT_SYSTEM_PROMPT}\n- Current local datetime: {current_datetime}.\n\n## Skill Capability Registry (Auto-Loaded)\n{skill_catalog}\n"


NORMAL_MODE_TOOL_GUIDANCE = """This chat can use Enchan CLI host runtime automatically. run_command is the primary open-ended local execution surface; typed helpers exist for safer inspection, editing, web, skills, and delegation.
If you want every turn to be forced through explicit ReAct tool mode, restart Enchan from your terminal with:

enchan --agent

Do not claim that shell commands typed inside the chat were executed. Shell launch commands must be run through run_command or in the user's terminal."""


def truncate_observation(text: str, max_chars: Optional[int] = None) -> str:
    limit = max_chars if max_chars is not None else get_max_obs_chars()
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    warning = f"[SYSTEM TRUNCATION WARNING: output truncated to {limit} chars; {omitted} chars omitted.]\n"
    budget = max(500, limit - len(warning))
    return warning + text[:budget] + f"\n[truncated {len(text) - budget} chars]"


def resolve_workspace_path(raw_path: str, *, require_file: bool = False, require_inside_cli: bool = False) -> Path:
    path = Path(str(raw_path).strip("\"'"))
    root = Path.cwd()
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    if require_inside_cli and path != root and root not in path.parents:
        raise ValueError(f"Refusing path outside workspace: {path}")
    if require_file and (not path.exists() or not path.is_file()):
        raise FileNotFoundError(f"File not found: {path}")
    return path


def make_unified_diff(path: Path, before: str, after: str) -> str:
    return "\n".join(difflib.unified_diff(before.splitlines(), after.splitlines(), fromfile=str(path), tofile=str(path), lineterm=""))


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


def _decode_smart(data: bytes) -> str:
    if not data:
        return ""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp932", errors="replace")


def _estimate_tokens(text: str, tokenizer=None) -> int:
    if tokenizer is not None:
        try:
            from backend.context_compression import count_text_tokens
            return count_text_tokens(tokenizer, text)
        except Exception:
            pass
    try:
        from backend.enchan_chat import estimate_text_tokens_rough
        return estimate_text_tokens_rough(text)
    except Exception:
        return int(len(text) / 1.5)


def _compress_text(text: str, source_label: str, query: str, *, tokenizer=None, model=None) -> dict:
    if not query:
        return {"ok": False, "error": "mode='compress' requires a 'query' argument."}
    from backend.reading_agent import execute_reading_pipeline
    import contextlib
    import io

    estimated_tokens = _estimate_tokens(text, tokenizer=tokenizer)
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        compressed, metadata = execute_reading_pipeline(text, source_label, query, tokenizer=tokenizer, source_tokens=estimated_tokens, model=model)
    metrics = captured.getvalue().strip()
    if READ_DOCUMENT_DEBUG and metrics:
        prefix = f"{source_label} (Compressed view for query: '{query}')\nSource: {len(text)} chars, ~{estimated_tokens} tokens\n\n{metrics}"
    else:
        prefix = f"{source_label} (Structured compressed view for query: '{query}')\nSource: {len(text)} chars, ~{estimated_tokens} tokens"
    if estimated_tokens > 5000:
        prefix += "\n[WARNING: Large file]"
    return {"ok": True, "content": truncate_observation(prefix + "\n\n" + compressed, max_chars=COMPRESSED_DOCUMENT_MAX_CHARS), "observation_max_chars": COMPRESSED_DOCUMENT_MAX_CHARS}


def tool_read_file(args: dict) -> dict:
    raw_path = args.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return {"ok": False, "error": "read_file requires path."}
    try:
        path = resolve_workspace_path(raw_path, require_file=True)
    except (OSError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    text = "".join(lines)
    tokenizer = args.get("__tokenizer")
    model = args.get("__model")
    tokens = _estimate_tokens(text, tokenizer=tokenizer)
    mode = args.get("mode", "raw")
    if mode == "raw" and tokens > 5000 and not args.get("lines"):
        mode = "compress"
        args["query"] = args.get("query") or "overall summary, main plot, key events, main characters"
    if mode == "compress":
        return _compress_text(text, str(path), str(args.get("query") or ""), tokenizer=tokenizer, model=model)
    try:
        start, end = parse_line_range(args.get("lines"))
    except ValueError as e:
        return {"ok": False, "error": f"Invalid lines value: {e}"}
    actual_start = start or 1
    if start is not None:
        end = len(lines) if end is None else min(end, len(lines))
        selected = lines[start - 1:end]
    else:
        selected = lines
    body = "".join(f"{idx}: {line}" for idx, line in enumerate(selected, actual_start))
    actual_end = end or (actual_start + len(selected) - 1)
    content = f"{path} lines {actual_start}-{actual_end} of {len(lines)} (Total size: {len(text)} chars, ~{tokens} tokens)\n{body}"
    limit = get_max_obs_chars()
    if len(content) > limit:
        return {"ok": False, "error": f"Requested raw content is too large ({len(content)} chars). Use a smaller line range or mode='compress'."}
    return {"ok": True, "content": content}


def _iter_search_files(root: Path):
    ignore_dirs = {".git", ".venv", ".venv_cuda", "__pycache__", "node_modules", ".idea", "dist", "build"}
    blocked_ext = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".webp", ".zip", ".exe", ".dll", ".pyc"}
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for name in files:
            path = Path(current_root) / name
            if path.suffix.lower() not in blocked_ext:
                yield path


def tool_search_code(args: dict) -> dict:
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"ok": False, "error": "search_code requires query."}
    query = query.strip()
    regex = bool(args.get("regex", False))
    context_lines = max(0, min(int(args.get("context_lines", 2) or 2), 5))
    max_results = max(1, min(int(args.get("max_results", 80) or 80), 200))
    try:
        root = resolve_workspace_path(str(args.get("path") or "."), require_inside_cli=True)
    except (OSError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    search_root = root.parent if root.is_file() else root
    rg = shutil.which("rg")
    if rg:
        cmd = [rg, "--line-number", "--with-filename", "--context", str(context_lines), "--max-count", str(max_results)]
        if not regex:
            cmd.append("--fixed-strings")
        cmd.append(query)
        completed = subprocess.run(cmd, cwd=str(search_root), capture_output=True, timeout=30)
        body = _decode_smart(completed.stdout) or "No matches."
        if completed.returncode not in (0, 1):
            body += "\nstderr:\n" + _decode_smart(completed.stderr)
        content = f"Search root: {search_root}\nquery: {query}\nengine: rg\n\n{body}"
    else:
        try:
            pattern = re.compile(query if regex else re.escape(query), re.IGNORECASE)
        except re.error as e:
            return {"ok": False, "error": f"Invalid regex: {e}"}
        hits = []
        scanned = 0
        for path in _iter_search_files(search_root):
            try:
                file_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except Exception:
                continue
            scanned += 1
            for idx, line in enumerate(file_lines, 1):
                if pattern.search(line):
                    start = max(1, idx - context_lines)
                    end = min(len(file_lines), idx + context_lines)
                    snippet = "\n".join(f"{n}: {file_lines[n - 1]}" for n in range(start, end + 1))
                    hits.append(f"--- {path.relative_to(search_root)}:{idx} ---\n{snippet}")
                    if len(hits) >= max_results:
                        break
            if len(hits) >= max_results:
                break
        content = f"Search root: {search_root}\nquery: {query}\nengine: python-fallback\nfiles_scanned: {scanned}\nresults: {len(hits)}\n\n" + ("\n\n".join(hits) if hits else "No matches.")
    if args.get("mode") == "compress":
        return _compress_text(content, f"search_code({query})", str(args.get("compress_query") or query), tokenizer=args.get("__tokenizer"), model=args.get("__model"))
    return {"ok": True, "content": truncate_observation(content, max_chars=20000), "observation_max_chars": 20000}


def tool_edit_file(args: dict) -> dict:
    apply_val = args.get("apply", True)
    should_apply = not (apply_val is False or str(apply_val).lower() == "false")
    patch = args.get("patch")
    if isinstance(patch, str) and patch.strip():
        if not should_apply:
            return {"ok": True, "content": "DRY RUN PATCH:\n" + patch}
        temp_dir = CLI_DIR / "temp_workspace"
        temp_dir.mkdir(exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".patch", dir=str(temp_dir), delete=False) as f:
            f.write(patch.replace("\r\n", "\n"))
            patch_file = Path(f.name)
        try:
            completed = subprocess.run(["git", "apply", "--whitespace=nowarn", str(patch_file)], cwd=str(CLI_DIR), capture_output=True, timeout=60)
            if completed.returncode != 0:
                return {"ok": False, "error": "git apply failed\nstdout:\n" + _decode_smart(completed.stdout) + "\nstderr:\n" + _decode_smart(completed.stderr)}
            return {"ok": True, "content": "APPLIED: patch updated the workspace. Run verification next.", "event": {"type": "edit_applied", "tool": "edit_file", "chars": len(patch), "applied": True}}
        finally:
            patch_file.unlink(missing_ok=True)
    path_value = args.get("path")
    if not isinstance(path_value, str) or not path_value.strip():
        return {"ok": False, "error": "edit_file requires path for replace/write operations."}
    try:
        path = resolve_workspace_path(path_value, require_inside_cli=True)
    except (OSError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    if "old" in args or "new" in args:
        old, new = args.get("old"), args.get("new")
        if not isinstance(old, str) or not isinstance(new, str):
            return {"ok": False, "error": "Exact replace requires string old and new."}
        before = path.read_text(encoding="utf-8", errors="replace")
        count = before.count(old)
        if count != 1:
            return {"ok": False, "error": f"Expected exactly one match, found {count}."}
        after = before.replace(old, new, 1)
        diff = make_unified_diff(path, before, after)
        if not should_apply:
            return {"ok": True, "content": "DRY RUN DIFF:\n" + diff}
        path.write_text(after, encoding="utf-8")
        return {"ok": True, "content": "APPLIED exact replacement.\n" + diff, "event": {"type": "edit_applied", "tool": "edit_file", "path": str(path), "applied": True}}
    if "content" in args:
        content = args.get("content")
        if not isinstance(content, str):
            return {"ok": False, "error": "content must be a string."}
        if path.exists() and not bool(args.get("overwrite", False)):
            return {"ok": False, "error": f"File exists: {path}. Set overwrite=true to replace it."}
        before = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        diff = make_unified_diff(path, before, content)
        if not should_apply:
            return {"ok": True, "content": "DRY RUN DIFF:\n" + diff}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"ok": True, "content": "WROTE file.\n" + diff, "event": {"type": "edit_applied", "tool": "edit_file", "path": str(path), "applied": True}}
    return {"ok": False, "error": "edit_file requires patch, old/new, or content."}


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


def _host_shell_argv(command: str, shell_name: Optional[str] = None) -> tuple[list[str], str]:
    shell_name = (shell_name or DEFAULT_HOST_SHELL).strip().lower()
    if shell_name in {"powershell", "pwsh", "ps"}:
        exe = shutil.which("pwsh") or shutil.which("powershell")
        if not exe:
            raise ValueError("PowerShell was requested but neither 'pwsh' nor 'powershell' was found on PATH.")
        if command.lower() == "pwd":
            command = "Get-Location"
        preamble = "[Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $OutputEncoding = [Console]::OutputEncoding; "
        return [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", preamble + command], "powershell"
    if shell_name in {"cmd", "cmd.exe"}:
        exe = shutil.which("cmd.exe")
        if not exe:
            raise ValueError("cmd was requested but 'cmd.exe' was not found on PATH.")
        return [exe, "/d", "/s", "/c", command], "cmd"
    if shell_name in {"sh", "bash"}:
        exe = shutil.which(shell_name)
        if not exe and shell_name == "sh" and Path("/bin/sh").exists():
            exe = "/bin/sh"
        if not exe:
            raise ValueError(f"{shell_name} was requested but it was not found on PATH.")
        return [exe, "-lc", command], shell_name
    raise ValueError("run_command shell must be powershell, cmd, sh, or bash.")


def tool_run_command(args: dict) -> dict:
    command = args.get("command") or args.get("cmd")
    if not isinstance(command, str) or not command.strip():
        return {"ok": False, "error": "run_command requires command."}
    command = command.strip()
    if command.lower() == "pwd":
        command = "Get-Location"
    try:
        cwd = _resolve_command_cwd(args)
        timeout_seconds = max(1, min(int(args.get("timeout_seconds", 30) or 30), 300))
        max_output_chars = max(1000, min(int(args.get("max_output_chars", get_max_obs_chars()) or get_max_obs_chars()), 500000))
        argv, shell_name = _host_shell_argv(command, str(args.get("shell")) if args.get("shell") else None)
        started = time.perf_counter()
        completed = subprocess.run(argv, cwd=str(cwd), shell=False, capture_output=True, timeout=timeout_seconds)
        elapsed = time.perf_counter() - started
        stdout = _decode_smart(completed.stdout)
        stderr = _decode_smart(completed.stderr)
        content = f"tool: run_command\nshell: {shell_name}\ncwd: {cwd}\ncommand: {command}\ntimeout_seconds: {timeout_seconds}\nduration_seconds: {elapsed:.3f}\nexit_code: {completed.returncode}\nstdout:\n{stdout}\nstderr:\n{stderr}"
        return {"ok": completed.returncode == 0, "content": truncate_observation(content, max_chars=max_output_chars)}
    except subprocess.TimeoutExpired as e:
        return {"ok": False, "error": f"run_command timed out after {e.timeout} seconds."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


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
        content = "\n".join(f"Title: {r.get('title')}\nURL: {r.get('url')}\nSnippet: {r.get('snippet')}\n" if "error" not in r else f"Error: {r['error']}" for r in results)
    return {"ok": True, "content": content}


def tool_web_browse(args: dict) -> dict:
    from backend.web_browse_service import browse_query, fetch_url
    url = args.get("url")
    query = args.get("query")
    max_pages = max(1, min(int(args.get("max_pages", 3) or 3), 5))
    max_chars = max(2000, min(int(args.get("max_chars_per_page", 12000) or 12000), 30000))
    if isinstance(url, str) and url.strip():
        page = fetch_url(url.strip(), max_chars=max_chars)
        if not page.get("ok"):
            return {"ok": False, "error": page.get("error", "web_browse failed."), "content": str(page)}
        content = f"Opened URL: {page.get('url')}\nTitle: {page.get('title') or '(no title)'}\nContent-Type: {page.get('content_type')}\n\n{page.get('text', '')}"
        return {"ok": True, "content": truncate_observation(content, max_chars=max_chars + 2000)}
    if isinstance(query, str) and query.strip():
        pages = browse_query(query.strip(), max_pages=max_pages, max_chars_per_page=max_chars)
        chunks = [f"Browse query: {query.strip()}"]
        ok_count = 0
        for index, page in enumerate(pages, 1):
            if page.get("ok"):
                ok_count += 1
                chunks.append(f"\n--- Page {index} ---\nURL: {page.get('url')}\nTitle: {page.get('title') or page.get('search_title') or '(no title)'}\nSearch snippet: {page.get('search_snippet') or ''}\n\n{page.get('text', '')}")
            else:
                chunks.append(f"\n--- Page {index} failed ---\nURL: {page.get('url') or ''}\nSearch title: {page.get('search_title') or ''}\nError: {page.get('error') or 'unknown error'}")
        if ok_count == 0:
            return {"ok": False, "error": "Search found pages, but none could be opened.", "content": "\n".join(chunks)}
        return {"ok": True, "content": truncate_observation("\n".join(chunks), max_chars=max_chars * max_pages + 4000)}
    return {"ok": False, "error": "web_browse requires either 'url' or 'query'."}


def tool_list_skills(args: dict) -> dict:
    from backend.skills_loader import list_registered_skills
    return {"ok": True, "content": list_registered_skills()}


def tool_use_skill(args: dict) -> dict:
    skill_name = args.get("skill_name") or args.get("name")
    argument = args.get("argument") or args.get("value") or ""
    method = args.get("method")
    params = args.get("params") if isinstance(args.get("params"), dict) else None
    if not skill_name:
        return {"ok": False, "error": "use_skill requires 'skill_name'."}
    if params is None and not argument:
        params = {}
    from contextlib import redirect_stderr, redirect_stdout
    from backend.skills_loader import SkillError, run_skill
    from backend.ui_theme import stream_agent_observation
    stream = stream_agent_observation("use_skill")
    ok = True
    content = ""
    try:
        with redirect_stdout(stream), redirect_stderr(stream):
            content = run_skill(str(skill_name), str(argument), method=str(method) if method else None, params=params)
        returned = str(content or "").strip()
        if returned and returned not in stream.getvalue():
            stream.write(("\n" if stream.getvalue().strip() else "") + returned + "\n")
    except SkillError as e:
        ok = False
        content = str(e)
        if content:
            stream.write(("\n" if stream.getvalue().strip() else "") + content + "\n")
    except Exception as e:
        ok = False
        content = f"Internal error while running skill '{skill_name}': {e}"
        stream.write(content + "\n")
    finally:
        stream.close()
    captured = stream.getvalue().strip()
    if captured:
        content = captured
    return {"ok": ok, "content": content, "displayed": True}


def _load_local_config() -> dict:
    path = CLI_DIR / "enchan_config.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _command_parts(value, default: list[str]) -> list[str]:
    if isinstance(value, list) and all(isinstance(part, str) for part in value):
        return [part for part in value if part]
    if isinstance(value, str) and value.strip():
        return shlex.split(value, posix=False)
    return list(default)


def tool_delegate_agent(args: dict) -> dict:
    agent = str(args.get("agent", "")).strip().lower()
    prompt = args.get("prompt") or args.get("argument") or args.get("value") or ""
    if agent not in {"codex", "gemini", "claude"}:
        return {"ok": False, "error": "delegate_agent requires agent='codex', 'gemini', or 'claude'."}
    if not isinstance(prompt, str) or not prompt.strip():
        return {"ok": False, "error": "delegate_agent requires a non-empty prompt."}
    cfg = _load_local_config()
    defaults = {"codex": ["codex", "exec"], "gemini": ["gemini", "--model", "gemini-3.5-flash", "--prompt"], "claude": ["claude"]}
    command = _command_parts(cfg.get(f"{agent}_command"), defaults[agent])
    if shutil.which(command[0]) is None:
        return {"ok": False, "error": f"External agent command not found on PATH: {command[0]}."}
    timeout = int(cfg.get(f"{agent}_timeout_seconds", cfg.get("delegate_timeout_seconds", 600)))
    try:
        completed = subprocess.run(command + [prompt.strip()], cwd=str(CLI_DIR), capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        return {"ok": False, "error": f"{agent} delegation timed out after {e.timeout} seconds."}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    content = f"agent: {agent}\ncwd: {CLI_DIR}\ncommand: {' '.join(command)} [prompt]\nexit_code: {completed.returncode}\nstdout:\n{_decode_smart(completed.stdout)}\nstderr:\n{_decode_smart(completed.stderr)}"
    return {"ok": completed.returncode == 0, "content": truncate_observation(content, max_chars=12000)}


TOOL_REGISTRY = {
    "search_code": tool_search_code,
    "read_file": tool_read_file,
    "edit_file": tool_edit_file,
    "run_command": tool_run_command,
    "web_search": tool_web_search,
    "web_browse": tool_web_browse,
    "list_skills": tool_list_skills,
    "use_skill": tool_use_skill,
    "delegate_agent": tool_delegate_agent,
}


def _interactive_security_prompt() -> bool:
    from backend.ui_theme import interactive_yes_no
    return interactive_yes_no("Allow execution?", default_yes=True)


def _tool_requires_permission(tool_name: str, args: dict) -> bool:
    if tool_name == "run_command":
        return False
    if tool_name == "edit_file":
        val = args.get("apply", True)
        return not (val is False or str(val).lower() == "false")
    if tool_name == "use_skill":
        return True
    return False


def execute_agent_tool(call: dict, tokenizer=None, model=None) -> dict:
    tool_name = call.get("tool")
    if tool_name == "_parse_error":
        return {"tool": tool_name, "ok": False, "observation": call.get("error", "Invalid tool call.")}
    tool = TOOL_REGISTRY.get(tool_name)
    if tool is None:
        available = ", ".join(sorted(TOOL_REGISTRY))
        return {"tool": tool_name, "ok": False, "observation": f"Unknown tool: {tool_name}. Available tools: {available}"}
    args = dict(call.get("args", {}))
    if _tool_requires_permission(tool_name, args):
        print(f"\n\x1b[38;2;190;170;120m⚠️  [Security Request]\x1b[0m \x1b[38;2;210;200;200mThe local Enchan AI wants to perform a sensitive action:\x1b[0m")
        print(f"  \x1b[38;2;210;200;200mTool: {tool_name}\x1b[0m")
        if tool_name == "edit_file":
            print(f"  \x1b[38;2;210;200;200mTarget: {args.get('path') or '[patch]'}\x1b[0m")
        elif tool_name == "use_skill":
            print(f"  \x1b[38;2;210;200;200mSkill: {args.get('skill_name') or args.get('name') or 'unknown'}\x1b[0m")
        if not _interactive_security_prompt():
            print("\x1b[38;2;180;100;100m  [System] Execution denied by user.\x1b[0m")
            return {"tool": tool_name, "ok": False, "observation": "User denied permission to execute this tool."}
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
