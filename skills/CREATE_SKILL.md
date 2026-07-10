# Creating a New Enchan Skill

Enchan can create a new local Skill when the existing Skill catalog does not provide the capability needed for a task.

## When to create one

Create a Skill when the capability will be reused, needs a clear typed interface, or should run as an isolated local process. For a one-off operation, prefer `run_command` or a temporary script.

## Minimal steps

1. Create a new folder under `skills/<skill_name>/`.
2. Add `skill.json` describing the runtime command, methods, input schemas, and minimum host capabilities.
3. Add a handler process that reads one JSON-RPC request per line from stdin and writes one JSON-RPC response per line to stdout.
4. Run `list_skills` and confirm the new Skill and its methods are loadable.
5. Test it with `use_skill` before relying on it in a user task.

## Minimal layout

```text
skills/
└── hello/
    ├── skill.json
    └── handler.py
```

`skills/hello/skill.json`:

```json
{
  "name": "hello",
  "description": "Return a greeting for a name.",
  "runtime": { "command": "python skills/hello/handler.py" },
  "methods": {
    "greet": {
      "description": "Create a greeting.",
      "input": {
        "type": "object",
        "properties": {
          "name": { "type": "string" }
        },
        "required": ["name"]
      }
    }
  },
  "host_capabilities": []
}
```

`skills/hello/handler.py`:

```python
import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    params = request.get("params", {})
    result = {"content": f"Hello, {params['name']}!"}
    response = {
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": result,
    }
    print(json.dumps(response, ensure_ascii=False), flush=True)
```

Test with:

```text
list_skills
use_skill(skill_name="hello", method="greet", params={"name":"Enchan"})
```

Use only the host capabilities the Skill actually requires: `read`, `write`, `bash`, `ask`, `log`, or `use_skill`.

For the complete manifest schema, callbacks, and JSON-RPC protocol, read `skills/README.md`.