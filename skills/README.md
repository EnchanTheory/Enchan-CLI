# Enchan CLI Skill System

This directory houses **Skills** specifically designed for Enchan CLI. These are modular components that can be auto-discovered by the Enchan Python backend and executed dynamically by the local LLM Agent.

## Directory Structure

```text
skills/
├── README.md                 # This specification document
└── <skill_name>/
    ├── skill_config.json     # [Required] Skill metadata and entrypoint definition
    └── <scripts>             # Any executable scripts (Python, JS, etc.)
```

## `skill_config.json` Schema

Each skill folder MUST contain a `skill_config.json` with the following keys:

- `name`: String. The unique identifier of the skill (matching folder name).
- `description`: String. Clear instructions explaining when the LLM agent should invoke this skill.
- `entrypoint`: String. The command executed to run this skill (e.g. `python skills/gemini_bridge/bridge.py`).

## Execution Flow

1. The Enchan LLM Agent checks for available skills via the `list_skills` tool.
2. If a task fits a skill's description, the agent executes `use_skill(skill_name, argument)`.
3. The backend executes the skill's defined `entrypoint` inside a subprocess, passing `argument` as a command-line argument.
4. The output (stdout/stderr) of the skill is returned to the agent as an observation.
