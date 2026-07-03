# Enchan CLI Skill System

Skills are long-lived or single-shot local processes that speak bidirectional JSON-RPC over stdio with the Enchan host.

This is the primary skill contract. The older `skill_config.json` entrypoint format still works, but it is treated as a legacy one-method wrapper named `invoke(argument)`.

## Directory Structure

```text
skills/
├── README.md
└── <skill_name>/
    ├── skill.json              # Preferred manifest for JSON-RPC skills
    ├── skill_config.json       # Legacy manifest, auto-wrapped when skill.json is absent
    └── <handler scripts>
```

## `skill.json` Schema

```json
{
  "name": "gitlab",
  "description": "GitLab issues and projects.",
  "runtime": { "command": "python skills/gitlab/handler.py" },
  "methods": {
    "search_issues": {
      "description": "Search issues in a project.",
      "input": {
        "type": "object",
        "properties": {
          "project": { "type": "string" },
          "state": { "type": "string", "enum": ["open", "closed", "all"], "default": "open" },
          "limit": { "type": "integer", "default": 10 }
        },
        "required": ["project"]
      }
    }
  },
  "host_capabilities": ["read", "ask", "log"]
}
```

Required fields:

- `name`: stable skill identifier, normally matching the folder name.
- `description`: when the agent should use the skill.
- `runtime.command`: command used to spawn the skill process. A string or argv array is accepted.
- `methods`: JSON-RPC methods exposed by the skill. Each method should declare an `input` JSON Schema.
- `host_capabilities`: host callbacks this skill may call. Use the minimum needed set.

The host validates the practical JSON Schema subset used for skill contracts: object inputs, `required`, `properties`, `type`, `enum`, and `default`.

Supported host callback capabilities:

- `host.log`: stream progress text to the caller.
- `host.ask`: ask the user for a missing detail.
- `host.read`: read a workspace document through Enchan's read tool.
- `host.write`: create or overwrite a workspace text file through Enchan's write tool.
- `host.bash`: run a host shell command through Enchan's shell tool.
- `host.use_skill`: call another skill through the same host dispatcher.

## Wire Protocol

Every message is one JSON object per line on stdio. Requests use JSON-RPC 2.0 shape:

```json
{ "jsonrpc": "2.0", "id": 1, "method": "search_issues", "params": { "project": "a/b", "limit": 5 } }
```

A skill returns either:

```json
{ "jsonrpc": "2.0", "id": 1, "result": { "content": "5 open issues...", "data": { "issues": [] } } }
```

or:

```json
{ "jsonrpc": "2.0", "id": 1, "error": { "message": "token expired" } }
```

Notifications have no `id` and do not require a reply:

```json
{ "jsonrpc": "2.0", "method": "log", "params": { "message": "querying..." } }
```

The skill may call back into the host with the same request shape:

```json
{ "jsonrpc": "2.0", "id": 7, "method": "host.read", "params": { "path": "README.md" } }
```

The host replies with the matching `id`.

## Minimal Python Skill

```python
import json
import sys

for line in sys.stdin:
    req = json.loads(line)
    params = req.get("params", {})
    result = {"content": f"hello {params.get('name', 'world')}"}
    print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": result}), flush=True)
```

## Execution Flow

1. The agent calls `list_skills()` to inspect skill contracts and method schemas.
2. The agent calls `use_skill(skill_name, argument)` for legacy-compatible one-shot use, or `use_skill(skill_name, method=<method>, params=<object>)` for typed methods.
3. The host starts or reuses the skill process and sends a JSON-RPC request over stdin.
4. The skill returns a JSON-RPC result, sends notifications, or calls permitted host capabilities.
5. Legacy `skill_config.json` skills are auto-wrapped as `invoke(argument)` so existing skills keep working.
