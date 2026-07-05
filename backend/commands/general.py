from pathlib import Path
from backend.core import registry

# Path resolution for LICENSE file
BACKEND_DIR = Path(__file__).resolve().parent.parent
CLI_DIR = BACKEND_DIR.parent

@registry.command("/help", desc="Show this help.")
def handle_help(file_context: str, **kwargs) -> tuple[bool, str, bool]:
    """Displays CLI Slash Commands and Smart Reading usage guide."""
    print("\n[Commands]")
    print("  /help                 Show this help.")
    print("  /license              Show repository license terms.")
    print("  /new                  Start a new session and clear current context.")
    print("  /status               Show active model, backend, context, and generation settings.")
    print("  /resume [num|name]    Resume a saved session.")
    print("  /model [num|name]     List or switch Ollama/Enchan models.")
    print("  /compress             Optimize older conversation turns invisibly.")
    print("  /set                  Show or change generation settings interactively.")
    print("  /set temp <value>     Set temperature, e.g. /set temp 0.3")
    print("  /set top_p <value>    Set top_p, e.g. /set top_p 0.9")
    print("  /set input <tokens>   Set max_input_tokens, e.g. /set input 4096")
    print("  /set max <tokens>     Set max_new_tokens, e.g. /set max 1024")
    print("  /exit                 Exit the CLI.")
    print("\n[Smart Reading]")
    print("  Paste or drag a file path and Enchan will read it directly.")
    print("  Large files are compressed internally with Enchan Engine; compressed context is hidden from display and logs.")
    print("  Ask naturally: summaries, characters, errors, settings, code behavior, or document analysis.")
    print("\n[Agent Tools]")
    print("  Enchan chooses tools when local evidence helps. Common tools include read_document, search_pattern, replace_text, write_text_file, and execute_command.")
    
    return True, file_context, False


@registry.command("/license", desc="Show repository license terms.")
def handle_license(file_context: str, **kwargs) -> tuple[bool, str, bool]:
    """Reads and prints the repository LICENSE file contents."""
    license_path = CLI_DIR / "LICENSE"
    try:
        print()
        print(license_path.read_text(encoding="utf-8").rstrip())
    except Exception as e:
        print(f"[Error] Failed to read LICENSE: {e}")
        
    return True, file_context, False


@registry.command("/status", desc="Show active model, backend, context, and generation settings.")
def handle_status(
    file_context: str,
    chat_history: list[dict],
    loaded_files: list[str],
    generation_config: dict,
    model=None,
    agent_mode: bool = False,
    **kwargs
) -> tuple[bool, str, bool]:
    """Prints runtime status of the active inference model, parameters, and session contexts."""
    model_id = model.config._name_or_path if model is not None and hasattr(model, "config") else generation_config.get("model_id", "ollama")
    enchan_config = getattr(model, "enchan_config", {}) if model is not None else {}
    
    print("\n[Status]")
    print(f"  Model: {model_id}")
    print(f"  Backend: {generation_config.get('backend', 'enchan')}")
    print(f"  Chat history messages: {len(chat_history)}")
    print(f"  Pending file context chars: {len(file_context)}")
    print(f"  Last loaded files: {len(loaded_files)}")
    print(f"  max_input_tokens: {generation_config.get('max_input_tokens', 'N/A')}")
    print(f"  max_new_tokens: {generation_config.get('max_new_tokens', 'N/A')}")
    print(f"  temperature: {generation_config.get('temperature', 'N/A')}")
    print(f"  top_p: {generation_config.get('top_p', 'N/A')}")
    print(f"  max_obs_chars: {generation_config.get('max_obs_chars', 10000)}")
    
    if enchan_config:
        print(f"  early_exit_threshold: {enchan_config.get('early_exit_threshold', 0.15)}")
        print(f"  force_early_exit_layer: {enchan_config.get('force_early_exit_layer', -1)}")
        
    print(f"  agent_mode: {agent_mode}")
    print(f"  Agent tools: {'active; forced tool-aware mode' if agent_mode else 'available; Enchan chooses when local evidence is needed'}")
    print(f"  Esc cancellation: enabled")
    
    return True, file_context, False
