import atexit
import json
import os
import shlex
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent
SKILLS_DIR = CLI_DIR / "skills"
DEFAULT_LEGACY_METHOD = "invoke"
_JSONRPC_VERSION = "2.0"
_SESSIONS: dict[str, "JsonRpcSkillSession"] = {}
_SESSIONS_LOCK = threading.Lock()


class SkillManifestError(Exception):
    pass


class JsonRpcSkillSession:
    """Persistent bidirectional JSON-RPC session over a skill process' stdio."""

    def __init__(self, skill_name: str, command: list[str], host_capabilities: list[str]):
        self.skill_name = skill_name
        self.command = command
        self.host_capabilities = set(host_capabilities or [])
        self.next_id = 1
        self.process: subprocess.Popen | None = None
        self.stderr_lines: list[str] = []
        self.stderr_thread: threading.Thread | None = None
        self.lock = threading.Lock()

    def is_alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self):
        if self.is_alive():
            return
        self.stderr_lines = []
        self.process = subprocess.Popen(
            self.command,
            cwd=str(CLI_DIR),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        self.stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self.stderr_thread.start()

    def close(self):
        process = self.process
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
        for stream in (process.stdin, process.stdout, process.stderr):
            try:
                if stream:
                    stream.close()
            except Exception:
                pass
        if self.stderr_thread is not None:
            self.stderr_thread.join(timeout=1)
        self.process = None

    def call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.start()
            request_id = self.next_id
            self.next_id += 1
            self._write({"jsonrpc": _JSONRPC_VERSION, "id": request_id, "method": method, "params": params})
            while True:
                line = self.process.stdout.readline()
                if line == "":
                    stderr = self._read_stderr_tail()
                    exit_code = self.process.poll()
                    self.close()
                    return {"error": {"message": f"Skill process exited before replying. Exit code: {exit_code}", "data": stderr}}
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    print(line, end="")
                    continue

                if message.get("id") == request_id and ("result" in message or "error" in message):
                    return message
                if "id" in message and isinstance(message.get("method"), str):
                    self._write(self._handle_host_request(message))
                    continue
                self._handle_notification(message)

    def _write(self, message: dict[str, Any]):
        if self.process is None or self.process.stdin is None:
            raise RuntimeError(f"Skill '{self.skill_name}' is not running.")
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def _drain_stderr(self):
        if self.process is None or self.process.stderr is None:
            return
        for line in self.process.stderr:
            self.stderr_lines.append(line)
            if len(self.stderr_lines) > 200:
                del self.stderr_lines[:100]

    def _read_stderr_tail(self) -> str:
        return "".join(self.stderr_lines[-50:]).strip()

    def _handle_notification(self, message: dict[str, Any]):
        method = message.get("method")
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        if method in {"log", "host.log"}:
            text = params.get("message") or params.get("content") or ""
            if text:
                print(str(text))

    def _handle_host_request(self, message: dict[str, Any]) -> dict[str, Any]:
        request_id = message.get("id")
        method = str(message.get("method") or "")
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        try:
            result = self._dispatch_host_request(method, params)
            return {"jsonrpc": _JSONRPC_VERSION, "id": request_id, "result": result}
        except Exception as e:
            return {"jsonrpc": _JSONRPC_VERSION, "id": request_id, "error": {"message": str(e)}}

    def _dispatch_host_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        capability = method.removeprefix("host.")
        if capability not in self.host_capabilities:
            raise PermissionError(f"Skill '{self.skill_name}' is not allowed to call host capability '{capability}'.")

        if capability == "log":
            text = params.get("message") or params.get("content") or ""
            if text:
                print(str(text))
            return {"ok": True}
        if capability == "ask":
            prompt = str(params.get("prompt") or "Skill requests input:")
            answer = input(prompt + " ")
            return {"answer": answer}
        if capability == "read":
            from agent_tools import tool_read_document
            return tool_read_document({"path": params.get("path"), "lines": params.get("lines"), "mode": params.get("mode", "raw"), "query": params.get("query")})
        if capability == "write":
            from agent_tools import tool_write_text_file
            return tool_write_text_file({"path": params.get("path"), "content": params.get("content"), "overwrite": params.get("overwrite", False)})
        if capability == "bash":
            from agent_tools import tool_host_shell
            return tool_host_shell({
                "command": params.get("command"),
                "cwd": params.get("cwd"),
                "shell": params.get("shell") or "powershell",
                "timeout_seconds": params.get("timeout_seconds", 30),
                "max_output_chars": params.get("max_output_chars", 12000),
            })
        if capability == "use_skill":
            nested_name = str(params.get("name") or params.get("skill_name") or "")
            if nested_name == self.skill_name:
                raise RuntimeError("A skill cannot synchronously call itself through host.use_skill.")
            nested_method = str(params.get("method") or DEFAULT_LEGACY_METHOD)
            nested_params = params.get("params") if isinstance(params.get("params"), dict) else None
            nested_argument = str(params.get("argument") or "")
            return {"ok": True, "content": run_skill(nested_name, nested_argument, method=nested_method, params=nested_params)}
        raise ValueError(f"Unknown host capability '{capability}'.")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise SkillManifestError(f"{path.name} must contain a JSON object.")
    return data


def _command_parts(value: Any) -> list[str]:
    if isinstance(value, list) and all(isinstance(part, str) for part in value):
        return [part for part in value if part]
    if isinstance(value, str) and value.strip():
        return shlex.split(value, posix=(os.name != "nt"))
    return []


def _runtime_command(runtime: Any) -> list[str]:
    command = runtime.get("command") if isinstance(runtime, dict) else runtime
    return _command_parts(command)


def _schema_for_method(manifest: dict[str, Any], method: str) -> dict[str, Any]:
    methods = manifest.get("methods") if isinstance(manifest.get("methods"), dict) else {}
    method_spec = methods.get(method) if isinstance(methods.get(method), dict) else {}
    input_schema = method_spec.get("input") if isinstance(method_spec.get("input"), dict) else {}
    return input_schema


def _validate_and_apply_defaults(schema: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    if not schema:
        return dict(params)
    schema_type = schema.get("type")
    if schema_type and schema_type != "object":
        raise SkillManifestError("Skill method input schema must be an object schema.")

    validated = dict(params)
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    for key, prop_schema in properties.items():
        if key not in validated and isinstance(prop_schema, dict) and "default" in prop_schema:
            validated[key] = prop_schema["default"]

    required = schema.get("required") if isinstance(schema.get("required"), list) else []
    missing = [key for key in required if key not in validated]
    if missing:
        raise SkillManifestError(f"Missing required skill params: {', '.join(str(key) for key in missing)}")

    for key, value in validated.items():
        prop_schema = properties.get(key)
        if isinstance(prop_schema, dict):
            _validate_schema_value(key, value, prop_schema)
    return validated


def _validate_schema_value(key: str, value: Any, schema: dict[str, Any]):
    allowed = schema.get("enum")
    if isinstance(allowed, list) and value not in allowed:
        raise SkillManifestError(f"Skill param '{key}' must be one of: {', '.join(map(str, allowed))}")

    expected = schema.get("type")
    if not expected:
        return
    expected_types = expected if isinstance(expected, list) else [expected]
    if any(_matches_json_type(value, type_name) for type_name in expected_types):
        return
    raise SkillManifestError(f"Skill param '{key}' must be type {expected}, got {type(value).__name__}.")


def _matches_json_type(value: Any, type_name: str) -> bool:
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "null":
        return value is None
    return True


def _legacy_manifest(skill_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": config.get("name", skill_dir.name),
        "description": config.get("description", "No description provided."),
        "runtime": {"command": config.get("entrypoint", "")},
        "methods": {
            DEFAULT_LEGACY_METHOD: {
                "description": "Run this legacy skill with one string argument.",
                "input": {
                    "type": "object",
                    "properties": {"argument": {"type": "string", "description": "Goal or details for the skill."}},
                    "required": ["argument"],
                },
            }
        },
        "host_capabilities": [],
        "legacy": True,
    }


def _load_skill_manifest(skill_dir: Path) -> tuple[dict[str, Any] | None, str | None]:
    skill_json = skill_dir / "skill.json"
    if skill_json.exists():
        try:
            manifest = _load_json(skill_json)
            if not isinstance(manifest.get("methods"), dict) or not manifest["methods"]:
                raise SkillManifestError("skill.json must define a non-empty methods object.")
            return manifest, None
        except Exception as e:
            return None, f"Error loading skill.json: {e}"

    legacy_config = skill_dir / "skill_config.json"
    if legacy_config.exists():
        try:
            return _legacy_manifest(skill_dir, _load_json(legacy_config)), None
        except Exception as e:
            return None, f"Error loading skill_config.json: {e}"

    return None, "Missing skill.json or skill_config.json"


def _manifest_for_skill(skill_name: str) -> tuple[Path, dict[str, Any]]:
    if not SKILLS_DIR.exists():
        raise SkillManifestError(f"Skills directory does not exist at {SKILLS_DIR}")
    skill_dir = SKILLS_DIR / skill_name
    if not skill_dir.exists() or not skill_dir.is_dir():
        raise SkillManifestError(f"Skill '{skill_name}' not found. Please run list_skills to verify names.")
    manifest, error = _load_skill_manifest(skill_dir)
    if error or manifest is None:
        raise SkillManifestError(f"Skill '{skill_name}' is not loadable: {error}")
    return skill_dir, manifest


def list_registered_skills() -> str:
    """List skill contracts discovered under skills/."""
    if not SKILLS_DIR.exists():
        return "No skills directory found."

    skills: list[str] = []
    for item in sorted(SKILLS_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not item.is_dir():
            continue
        manifest, error = _load_skill_manifest(item)
        if error:
            skills.append(f"- **{item.name}** ({error})")
            continue
        name = manifest.get("name", item.name)
        desc = manifest.get("description", "No description provided.")
        suffix = " [legacy auto-wrapped]" if manifest.get("legacy") else ""
        lines = [f"- **{name}**: {desc}{suffix}"]
        methods = manifest.get("methods") if isinstance(manifest.get("methods"), dict) else {}
        for method_name, method_spec in methods.items():
            method_desc = method_spec.get("description", "No description provided.") if isinstance(method_spec, dict) else "No description provided."
            input_schema = method_spec.get("input") if isinstance(method_spec, dict) else None
            schema_text = f" input={json.dumps(input_schema, ensure_ascii=False)}" if input_schema else ""
            lines.append(f"  - method `{method_name}`: {method_desc}{schema_text}")
        skills.append("\n".join(lines))

    if not skills:
        return "No valid skills registered in the skills/ directory."
    return "Available Enchan CLI Skills:\n" + "\n".join(skills)


def run_skill(skill_name: str, argument: str = "", *, method: str = DEFAULT_LEGACY_METHOD, params: dict[str, Any] | None = None) -> str:
    """Run a modern JSON-RPC skill method or a legacy auto-wrapped entrypoint."""
    try:
        skill_dir, manifest = _manifest_for_skill(skill_name)
        command = _runtime_command(manifest.get("runtime"))
        if not command:
            return f"[Error] Skill '{skill_name}' configuration has no runtime command defined."

        if manifest.get("legacy"):
            print(f"\n[System] Launching skill '{skill_name}'...")
            print(f"[System] Command: {' '.join(command)}")
            print("-" * 60)
            return _run_legacy_skill(skill_name, command, argument)

        methods = manifest.get("methods") if isinstance(manifest.get("methods"), dict) else {}
        if method not in methods:
            return f"[Error] Skill '{skill_name}' has no method '{method}'. Available methods: {', '.join(methods.keys())}"

        raw_params = params if isinstance(params, dict) else {"argument": argument}
        call_params = _validate_and_apply_defaults(_schema_for_method(manifest, method), raw_params)
        print(f"\n[System] Launching skill '{skill_name}'...")
        print(f"[System] Command: {' '.join(command)}")
        print("-" * 60)
        session = _session_for(skill_name, command, manifest)
        response = session.call(method, call_params)

        print("-" * 60)
        if "error" in response:
            error = response["error"]
            if isinstance(error, dict):
                message = error.get("message", "Unknown skill error")
                data = error.get("data") or ""
                return f"Skill '{skill_name}' failed.\nError: {message}\n{data}".strip()
            return f"Skill '{skill_name}' failed.\nError: {error}"

        result = response.get("result")
        if isinstance(result, dict):
            content = result.get("content")
            if content is None:
                content = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            content = str(result)
        print(f"[System] Skill '{skill_name}' method '{method}' completed.")
        return f"Skill '{skill_name}' completed.\nMethod: {method}\nOutput:\n{content}".strip()
    except Exception as e:
        return f"[Error] Failed to execute skill '{skill_name}': {e}"


def _session_for(skill_name: str, command: list[str], manifest: dict[str, Any]) -> JsonRpcSkillSession:
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(skill_name)
        if session is None or session.command != command or not session.is_alive():
            session = JsonRpcSkillSession(skill_name, command, manifest.get("host_capabilities", []))
            _SESSIONS[skill_name] = session
        return session


def close_all_sessions():
    with _SESSIONS_LOCK:
        sessions = list(_SESSIONS.values())
        _SESSIONS.clear()
    for session in sessions:
        session.close()


atexit.register(close_all_sessions)


def _run_legacy_skill(skill_name: str, command: list[str], argument: str) -> str:
    cmd_parts = command + [argument]
    try:
        process = subprocess.Popen(
            cmd_parts,
            cwd=str(CLI_DIR),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        captured_output: list[str] = []
        for line in iter(process.stdout.readline, ""):
            sys.stdout.write(line)
            sys.stdout.flush()
            captured_output.append(line)

        process.stdout.close()
        process.wait()
        stdout_str = "".join(captured_output).strip()

        print("-" * 60)
        print(f"[System] Legacy skill '{skill_name}' execution completed with exit code {process.returncode}.")

        obs = f"Skill '{skill_name}' completed. Exit code: {process.returncode}.\n"
        if stdout_str:
            obs += f"Output:\n{stdout_str}\n"
        return obs
    except Exception as e:
        return f"[Error] Failed to execute legacy skill '{skill_name}': {e}"
