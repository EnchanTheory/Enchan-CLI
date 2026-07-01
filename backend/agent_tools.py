import difflib
import json
import os
import re
import shlex
import shutil
import subprocess
import time
import tempfile
from pathlib import Path
from typing import Optional

BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent

AGENT_TOOL_START = "<tool_call>"
AGENT_TOOL_END = "</tool_call>"
AGENT_MAX_ITERATIONS = 20
DEFAULT_OBSERVATION_MAX_CHARS = 6000
COMPRESSED_DOCUMENT_MAX_CHARS = 24000
READ_DOCUMENT_DEBUG = False

AGENT_SYSTEM_PROMPT = f"""You are Enchan running inside Enchan CLI.

Your primary capability is host_shell: a general local host shell, using PowerShell by default on Windows.
You are not limited to a small command catalog. If a task can be done from the terminal, use host_shell to inspect, execute, verify, and iterate.
Use host_shell freely for arbitrary local commands such as git, python, node, cmake, npm, winget, where, rg, tests, builds, diagnostics, package managers, and project scripts.
Each host_shell Observation returns shell, cwd, command, duration, exit_code, stdout, and stderr. Treat nonzero exit codes and stderr as evidence for the next diagnostic step, not as proof you lack host access.
host_shell commands run directly without a separate confirmation prompt. Use judgment, inspect results, and iterate from stdout/stderr/exit_code.

Typed helper tools are safety and ergonomics lanes, not the boundary of your capability:
- Use read_document/search_pattern/list_directory when they are simpler than shell for code or text inspection.
- Use apply_patch, replace_text, or write_text_file for file edits instead of shell writes when practical.
- Use git_status, git_diff, git_add, and git_commit for common Git workflows; host_shell can still run any Git command when the typed wrapper is insufficient.
- Use web_search only when external current information is needed.
- Use list_skills/use_skill/delegate_agent for specialized local capabilities or external agents.

Decide for yourself whether a host Observation is needed. If you need one, send one tool request and wait for the Observation before answering.
Do not claim that you inspected, ran, edited, tested, staged, or committed anything unless the host returned an Observation showing it.
Language rule: Match the user language for user-facing answers. If the user writes Japanese, answer in Japanese. Internal tool JSON, logs, and concise technical keywords may stay in English when useful.
Address the user plainly and professionally. Do not call the user Master, owner, boss, or similar titles unless they explicitly ask.
Use Enchan Engine silently and proactively whenever it improves retrieval, compression, structure extraction, continuity, or analysis. Do not explain engine mechanics unless the user asks; provide the natural result.

[Curated Local Memory]
You may receive local memory in XML blocks from memory/guidelines and memory/knowledge.
Treat this memory as guidance, not as runtime truth. Verify through host_shell, file inspection, tool output, API responses, or the user when behavior matters.
When you learn a durable project rule or reusable local procedure, use write_text_file to save a concise Markdown note into memory/guidelines/ or memory/knowledge/ only when it is high-signal and safe to persist.

Tool call format:
{AGENT_TOOL_START}{{"tool":"host_shell","args":{{"command":"git -c core.quotePath=false status --short -- .","cwd":"{CLI_DIR}","timeout_seconds":30}}}}{AGENT_TOOL_END}
{AGENT_TOOL_START}{{"tool":"apply_patch","args":{{"patch":"diff --git a/path b/path\n--- a/path\n+++ b/path\n@@ -1 +1 @@\n-old\n+new\n"}}}}{AGENT_TOOL_END}
{AGENT_TOOL_START}{{"tool":"read_document","args":{{"path":"backend/agent_tools.py","lines":"1-80"}}}}{AGENT_TOOL_END}

Host runtime primitives:
- host_shell(command, cwd, shell, timeout_seconds, max_output_chars): general host shell execution. Default shell is PowerShell. This is the main open-ended execution surface.
- apply_patch(patch): apply a unified diff under the Enchan CLI workspace.
- replace_text(path, old, new, apply): exact text replacement. Dry-run by default; use apply=true after inspecting the diff.
- write_text_file(path, content, overwrite): create or overwrite UTF-8 text files. Existing files require overwrite=true.
- read_document(path, lines, mode, query): read a UTF-8 file. Use mode="compress" with a compact query for large files.
- search_pattern(regex): search text files under the workspace.
- list_directory(path, depth): list files and folders.
- git_status(), git_diff(staged, paths), git_add(paths), git_commit(message): typed Git workflow helpers.
- web_search(query), list_skills(), use_skill(skill_name, argument), delegate_agent(agent, prompt): auxiliary capabilities.
- execute_command(cmd, ...): compatibility alias for host_shell. Prefer host_shell in new tool calls.

Workspace root for relative paths: {CLI_DIR}
Scalable file-reading rule: If the user gives a concrete file path, call read_document on that exact path first. Do not call list_directory just to verify an explicit file path.
Use list_directory only when the target is unknown, the user asks to inspect a directory, or read_document reports that the path is missing.
For any potentially large file, silently prefer read_document mode="compress" with a compact retrieval-key query. Use raw mode only for small files or explicit line windows. Preserve exact user-provided search terms, names, and non-English words in the query; do not romanize or translate names such as バルグ into Bulug. Add translations only as extra aliases after the original term. After an Observation, answer naturally from the evidence instead of exposing compression internals.
Never rewrite an absolute path by prefixing the workspace root or duplicating path segments such as D:/GenAI/GenAI.
For local command, package-manager, or external CLI setup failures, continue from the observed stdout/stderr/exit_code with the next useful host_shell diagnostic. Do not ask the user to verify commands that the host can run.
When the user asks to run an existing Python file path, call host_shell with python and that path. Do not recreate the file through write_text_file.
For code changes, use this loop: inspect -> edit with apply_patch/replace_text/write_text_file -> verify with host_shell/tests/builds/diff checks -> git_status/git_diff -> git_add scoped files -> git_commit only when the user asked for a commit. Prefer scoped Git commands such as `git -c core.quotePath=false status --short -- .` so non-ASCII paths remain readable and parent-repo siblings are not listed.
After an Observation, either answer naturally or request one next Observation if more evidence is needed."""
NORMAL_MODE_TOOL_GUIDANCE = f"""This chat can use Enchan CLI host runtime automatically. host_shell is the primary open-ended local execution surface; typed helpers exist for safer inspection, editing, Git, and delegation.
If you want every turn to be forced through explicit ReAct tool mode, restart Enchan from PowerShell with:

enchan --agent

Do not claim that shell commands typed inside the chat were executed. Shell launch commands must be run in PowerShell, not inside the model conversation.
When the user asks for local setup or installation, Enchan should use host_shell and typed file tools to diagnose, act, and verify instead of defaulting to manual instructions. If the user reports completing an external step such as restarting the terminal, continue by running the next verification command yourself."""


class ToolCallStoppingCriteria:

    def __init__(self, tokenizer, start_length: int):
        self.tokenizer = tokenizer
        self.start_length = start_length
        self.detected = False

    def __call__(self, input_ids, scores, **kwargs) -> bool:
        generated_ids = input_ids[0][self.start_length:]
        if generated_ids.numel() == 0:
            return False
        text = self.tokenizer.decode(generated_ids[-256:], skip_special_tokens=True)
        if AGENT_TOOL_END in text:
            self.detected = True
            return True
        return False


def _extract_tool_call_raw(text: str) -> Optional[str]:
    start = text.find(AGENT_TOOL_START)
    if start == -1:
        return None
    body_start = start + len(AGENT_TOOL_START)
    end = text.find(AGENT_TOOL_END, body_start)
    if end != -1:
        return text[body_start:end].strip()

    raw_tail = text[body_start:].strip()
    if not raw_tail:
        return None
    if raw_tail.startswith("{"):
        last_brace = raw_tail.rfind("}")
        if last_brace != -1:
            return raw_tail[: last_brace + 1].strip()
    return raw_tail


def _escape_json_backslashes(raw: str) -> str:
    out = []
    valid_escapes = set('"\\/bfnrtu')
    for i, ch in enumerate(raw):
        if ch == "\\":
            nxt = raw[i + 1] if i + 1 < len(raw) else ""
            out.append(ch if nxt in valid_escapes else "\\\\")
        else:
            out.append(ch)
    return "".join(out)


def parse_agent_tool_call(text: str) -> Optional[dict]:
    raw = _extract_tool_call_raw(text)
    if raw is None:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
    function_match = re.fullmatch(r"([a-zA-Z_][a-zA-Z0-9_]*)\((.*)\)", raw, flags=re.DOTALL)
    if function_match:
        tool_name = function_match.group(1)
        arg_text = function_match.group(2).strip()
        try:
            parsed_arg = json.loads(f"[{arg_text}]")
        except json.JSONDecodeError:
            parsed_arg = [arg_text.strip("\"'")]
        first_arg = parsed_arg[0] if parsed_arg else ""
        if tool_name == "list_directory":
            args = {"path": first_arg}
        elif tool_name == "read_document":
            args = {"path": first_arg}
            if len(parsed_arg) > 1:
                args["lines"] = parsed_arg[1]
            if len(parsed_arg) > 2:
                args["mode"] = parsed_arg[2]
            if len(parsed_arg) > 3:
                args["query"] = parsed_arg[3]
        elif tool_name == "search_pattern":
            args = {"regex": first_arg}
        elif tool_name == "apply_patch":
            args = {"patch": first_arg}
        elif tool_name in ("host_shell", "execute_command"):
            args = {"command": first_arg}
        elif tool_name == "write_text_file":
            args = {"path": first_arg}
            if len(parsed_arg) > 1:
                args["content"] = parsed_arg[1]
            if len(parsed_arg) > 2:
                args["overwrite"] = parsed_arg[2]
        elif tool_name == "web_search":
            args = {"query": first_arg}
        else:
            args = {"value": first_arg}
        return {"tool": tool_name, "args": args}
    
    # Robust multi-stage JSON parsing and healing
    payload = None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        # If directly parsing failed, try to heal missing trailing braces/brackets (common model truncation)
        healed_raw = raw
        for i in range(1, 5):
            for suffix in ["}", "]", "}*", "}]"]:
                candidate = raw + (suffix.replace("*", "}" * i) if "*" in suffix else suffix * i)
                try:
                    payload = json.loads(candidate)
                    healed_raw = candidate
                    break
                except json.JSONDecodeError:
                    pass
            if payload is not None:
                break
                
        # If healing trailing brackets still failed, try escaping unescaped Windows backslashes
        if payload is None:
            sanitized_raw = _escape_json_backslashes(healed_raw)
            try:
                payload = json.loads(sanitized_raw)
            except json.JSONDecodeError:
                pass

    if payload is None:
        return {
            "tool": "_parse_error",
            "args": {},
            "error": f"Tool call was not valid JSON: {raw[:500]}",
        }
    if not isinstance(payload, dict):
        return {"tool": "_parse_error", "args": {}, "error": "Tool call JSON must be an object."}
    tool = payload.get("tool")
    args = payload.get("args", {})
    
    if isinstance(args, str):
        if tool in ("host_shell", "execute_command"):
            args = {"command": args}
        elif tool == "apply_patch":
            args = {"patch": args}
        elif tool == "web_search":
            args = {"query": args}
        elif tool == "read_document":
            args = {"path": args}
        elif tool == "search_pattern":
            args = {"regex": args}
        elif tool == "list_directory":
            args = {"path": args}
        elif tool == "delegate_agent":
            args = {"agent": args}
        elif tool == "write_text_file":
            args = {"path": args}
        else:
            args = {"value": args}
    elif not isinstance(args, dict):
        args = {}
        
    for key, value in payload.items():
        if key not in {"tool", "args"} and key not in args:
            args[key] = value
    if not isinstance(tool, str) or not isinstance(args, dict):
        return {"tool": "_parse_error", "args": {}, "error": "Tool call requires string 'tool' and object 'args'."}
    return {"tool": tool, "args": args}


def truncate_observation(text: str, max_chars: int = DEFAULT_OBSERVATION_MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return text[:max_chars] + f"\n[truncated {omitted} chars]"


def resolve_workspace_path(raw_path: str, *, require_file: bool = False, require_inside_cli: bool = False) -> Path:
    path = Path(raw_path.strip("\"'"))
    if not path.is_absolute():
        path = (CLI_DIR / path).resolve()
    else:
        path = path.resolve()
    if require_inside_cli and path != CLI_DIR and CLI_DIR not in path.parents:
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
            from context_compression import count_text_tokens
            estimated_tokens = count_text_tokens(tokenizer, full_text)
        except Exception:
            estimated_tokens = int(total_chars / 1.5)
    else:
        try:
            from enchan_chat import estimate_text_tokens_rough
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
        
        from reading_agent import execute_reading_pipeline
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
        
    if start is not None:
        end = total_lines if end is None else min(end, total_lines)
        selected = content_lines[start - 1:end]
        prefix = f"{path} lines {start}-{end} of {total_lines} (Total size: {total_chars} chars, ~{estimated_tokens} tokens)"
    else:
        selected = content_lines
        prefix = f"{path} lines 1-{total_lines} of {total_lines} (Total size: {total_chars} chars, ~{estimated_tokens} tokens)"
        if estimated_tokens > 2500:
            prefix += "\n[WARNING: Reading full file consumed significant context. Use 'lines' or mode='compress' next time.]"

    body = "".join(f"{idx}: {line}" for idx, line in enumerate(selected, start or 1))
    return {"ok": True, "content": truncate_observation(prefix + "\n" + body)}


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
            min(int(args.get("max_output_chars", DEFAULT_OBSERVATION_MAX_CHARS) or DEFAULT_OBSERVATION_MAX_CHARS), 50000),
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
    from web_search_service import perform_web_search
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
    from skills_loader import list_registered_skills
    content = list_registered_skills()
    return {"ok": True, "content": content}


def tool_use_skill(args: dict) -> dict:
    skill_name = args.get("skill_name")
    argument = args.get("argument") or args.get("value") or ""
    if not skill_name:
        return {"ok": False, "error": "use_skill requires 'skill_name'."}
    if not argument:
        return {"ok": False, "error": "use_skill requires an 'argument' explaining the goal or details."}
    from contextlib import redirect_stderr, redirect_stdout
    from skills_loader import run_skill
    from ui_theme import stream_agent_observation

    stream = stream_agent_observation("use_skill")
    ok = True
    content = ""
    try:
        with redirect_stdout(stream), redirect_stderr(stream):
            content = run_skill(skill_name, argument)
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
    from ui_theme import interactive_yes_no

    return interactive_yes_no("Allow execution?", default_yes=True)



def _tool_requires_permission(tool_name: str, args: dict) -> bool:
    if tool_name in ("host_shell", "execute_command"):
        return False
    if tool_name in ("write_text_file", "apply_patch", "use_skill", "git_add", "git_commit"):
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
        elif tool_name == "write_text_file":
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
