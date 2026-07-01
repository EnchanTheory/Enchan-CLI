import subprocess
import sys
import shutil
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("[Bridge Error] No task argument specified.")
        sys.exit(1)
        
    # Pre-flight check: Ensure ripgrep is installed to prevent Gemini CLI from using a buggy fallback
    if not shutil.which("rg"):
        print("[Bridge Error] 'ripgrep' (rg.exe) is not installed or not in PATH.")
        print("               Gemini CLI requires ripgrep for efficient codebase searching.")
        print("               Please install ripgrep (e.g., via 'choco install ripgrep' or 'winget install ripgrep') and try again.")
        sys.exit(1)
        
    task_argument = sys.argv[1]
    
    # 1. Draft a comprehensive prompt file for Gemini CLI to read from
    temp_task_path = Path("temp_gemini_task.md")
    
    # Identify CLI_DIR to keep paths robust
    cli_dir = Path(__file__).resolve().parent.parent.parent
    
    prompt_content = f"""# Enchan CLI Delegation Task

You are Gemini CLI (gemini-3.5-flash) called from inside Enchan CLI.
Enchan CLI (running a local model) has delegated a complex task to you because it requires advanced reasoning or direct codebase modifications.

## Your Goal / Directive:
{task_argument}

## Context:
- Current workspace directory: `{cli_dir}`

## Instructions:
1. Perform the requested modifications or research directly in this workspace.
2. Update the code, fix bugs, or add features securely and safely.
3. Be professional, direct, and concise. Avoid unnecessary conversational filler.
4. If you need to read files (like logs or JSONL files), use your built-in `read_file` or `grep_search` tools. Do NOT try to use `run_shell_command` or execute Python scripts to read files.
5. Once you are done and have verified your changes, inform the user, clean up any temporary state, and exit.
"""
    
    try:
        temp_task_path.write_text(prompt_content, encoding="utf-8")
    except Exception as e:
        print(f"[Bridge Error] Failed to write temporary prompt file: {e}")
        sys.exit(1)

    # 2. Run Gemini CLI
    print("\n>>> [Bridge] Delegating task to Gemini CLI...")
    print(f">>> [Bridge] Spawning globally installed Gemini CLI...")
    print("-" * 60)
    
    try:
        # Launch Gemini CLI. We MUST use --prompt and specify the model to use gemini-3.5-flash.
        executable = "gemini.cmd" if sys.platform == "win32" else "gemini"
        result = subprocess.run(
            [executable, "--model", "gemini-3.5-flash", "--yolo", "--prompt", "Please read temp_gemini_task.md and execute the requested instructions. Let me know when you are done."],
            shell=(sys.platform == "win32"), # Use shell=True on Windows for .cmd execution
            stdin=subprocess.DEVNULL,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        print("-" * 60)
        print(f"<<< [Bridge] Gemini CLI session ended with exit code {result.returncode}.")
    except Exception as e:
        print("-" * 60)
        print(f"[Bridge Error] Failed to launch Gemini CLI. Ensure 'gemini' is globally installed and on your PATH. Error: {e}")
    finally:
        # 3. Clean up the temporary file
        if temp_task_path.exists():
            try:
                temp_task_path.unlink()
            except Exception as e:
                print(f"[Bridge Warning] Failed to clean up temp_gemini_task.md: {e}")

if __name__ == "__main__":
    main()
