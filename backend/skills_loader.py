import os
import json
import sys
import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent
SKILLS_DIR = CLI_DIR / "skills"

def list_registered_skills() -> str:
    """Scans the skills/ directory and lists all valid registered skills."""
    if not SKILLS_DIR.exists():
        return "No skills directory found."
    
    skills = []
    for item in SKILLS_DIR.iterdir():
        if item.is_dir():
            config_file = item / "skill_config.json"
            if config_file.exists():
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    name = config.get("name", item.name)
                    desc = config.get("description", "No description provided.")
                    skills.append(f"- **{name}**: {desc}")
                except Exception as e:
                    skills.append(f"- **{item.name}** (Error loading config: {e})")
                    
    if not skills:
        return "No valid skills registered in the skills/ directory."
        
    return "Available Enchan CLI Skills:\n" + "\n".join(skills)

def run_skill(skill_name: str, argument: str) -> str:
    """Runs a registered skill's entrypoint, passing the argument."""
    if not SKILLS_DIR.exists():
        return f"[Error] Skills directory does not exist at {SKILLS_DIR}"
        
    skill_dir = SKILLS_DIR / skill_name
    if not skill_dir.exists() or not skill_dir.is_dir():
        return f"[Error] Skill '{skill_name}' not found. Please run list_skills to verify names."
        
    config_file = skill_dir / "skill_config.json"
    if not config_file.exists():
        return f"[Error] Skill '{skill_name}' is missing skill_config.json."
        
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        entrypoint = config.get("entrypoint")
        if not entrypoint:
            return f"[Error] Skill '{skill_name}' configuration has no 'entrypoint' defined."
            
        # We run the command inside the CLI_DIR (workspace root) to keep paths consistent
        # We append the argument safely. On Windows, subprocess with shell=True works perfectly with absolute execution.
        print(f"\n[System] Launching skill '{skill_name}'...")
        print(f"[System] Command: {entrypoint} [argument]")
        print("-" * 60)
        
        # Build command with argument.
        # We pass the argument as a separate CLI argument to the subprocess.
        # If entrypoint is e.g. "python skills/gemini_bridge/bridge.py", we split it and append the argument.
        cmd_parts = entrypoint.split()
        cmd_parts.append(argument)
        
        # Execute with Popen to stream output in real-time while capturing it for the LLM.
        # We redirect stderr to stdout to simplify real-time streaming and capturing.
        process = subprocess.Popen(
            cmd_parts,
            cwd=str(CLI_DIR),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1  # Line buffered
        )
        
        captured_output = []
        # Read output line by line in real-time
        for line in iter(process.stdout.readline, ''):
            sys.stdout.write(line)
            sys.stdout.flush()
            captured_output.append(line)
            
        process.stdout.close()
        process.wait()
        
        stdout_str = "".join(captured_output).strip()
        
        print("-" * 60)
        print(f"[System] Skill '{skill_name}' execution completed with exit code {process.returncode}.")
        
        # Construct the observation payload for the LLM
        obs = f"Skill '{skill_name}' completed. Exit code: {process.returncode}.\n"
        if stdout_str:
            obs += f"Output:\n{stdout_str}\n"
            
        return obs
        
    except Exception as e:
        return f"[Error] Failed to execute skill '{skill_name}': {e}"
