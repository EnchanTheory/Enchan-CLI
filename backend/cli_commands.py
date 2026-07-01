import os
import sys
import shutil
import urllib.request
import json
import re
from pathlib import Path
from typing import Optional

# Path Resolution
BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent


from ui_theme import interactive_menu, styled_input

from session_log import (
    append_session_event,
    list_session_logs,
    load_session_messages,
    resolve_session_log,
    get_session_metadata,
)


NATURAL_LANGUAGE_ARG_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff01-\uff5e]|[。、「」？]")


def looks_like_natural_language_arg(value: str) -> bool:
    if not value:
        return False
    return bool(NATURAL_LANGUAGE_ARG_RE.search(value))


def load_local_config() -> dict:
    config_path = CLI_DIR / "enchan_config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Warning] Failed to load config: {e}")
    return {}

def save_local_config(config: dict):
    config_path = CLI_DIR / "enchan_config.json"
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[Warning] Failed to save config: {e}")

def sync_generation_config_to_active_model(generation_config: dict, active_model_name: str, backend_mode: str):
    """Loads official model recommendations, merges with user-set JSON overrides, and updates generation_config in-place."""
    local_cfg = load_local_config()
    
    # 1. Start with system baseline defaults
    default_params = {
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 40,
        "presence_penalty": 0.0,
        "yarn_factor": 1.0,
        "max_new_tokens": -1,
        "max_input_tokens": 131072,
    }
    
    # 2. Try loading official recommended params from the Ollama Modelfile manifest
    if active_model_name and backend_mode in ("ollama", "enchan"):
        try:
            from enchan_llama_backend import resolve_ollama_model_to_blob
            _, official_params = resolve_ollama_model_to_blob(active_model_name)
            if official_params:
                if "temperature" in official_params:
                    default_params["temperature"] = float(official_params["temperature"])
                if "top_p" in official_params:
                    default_params["top_p"] = float(official_params["top_p"])
                if "top_k" in official_params:
                    default_params["top_k"] = int(official_params["top_k"])
                if "presence_penalty" in official_params:
                    default_params["presence_penalty"] = float(official_params["presence_penalty"])
        except Exception:
            pass
            
    # 3. Apply user-set manual overrides from enchan_config.json IF THEY EXIST
    if "temperature" in local_cfg:
        default_params["temperature"] = float(local_cfg["temperature"])
    if "top_p" in local_cfg:
        default_params["top_p"] = float(local_cfg["top_p"])
    if "top_k" in local_cfg:
        default_params["top_k"] = int(local_cfg["top_k"])
    if "presence_penalty" in local_cfg:
        default_params["presence_penalty"] = float(local_cfg["presence_penalty"])
    if "max_new_tokens" in local_cfg:
        default_params["max_new_tokens"] = int(local_cfg["max_new_tokens"])
    if "ollama_ctx" in local_cfg:
        default_params["max_input_tokens"] = int(local_cfg["ollama_ctx"])
    if "yarn_factor" in local_cfg:
        default_params["yarn_factor"] = float(local_cfg["yarn_factor"])
        
    # 4. Synchronize all values back to the generation_config in-place
    generation_config["temperature"] = default_params["temperature"]
    generation_config["top_p"] = default_params["top_p"]
    generation_config["top_k"] = default_params["top_k"]
    generation_config["presence_penalty"] = default_params["presence_penalty"]
    generation_config["yarn_factor"] = default_params["yarn_factor"]
    generation_config["max_new_tokens"] = default_params["max_new_tokens"]
    generation_config["max_input_tokens"] = default_params["max_input_tokens"]

def print_cli_help():
    print("\n[Commands]")
    print("  /help                 Show this help.")
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
    print("  /exit, /quit          Exit the CLI.")
    print("\n[Smart Reading]")
    print("  Paste or drag a file path and Enchan will read it directly.")
    print("  Large files are compressed internally with Enchan Engine; compressed context is hidden from display and logs.")
    print("  Ask naturally: summaries, characters, errors, settings, code behavior, or document analysis.")
    print("\n[Agent Tools]")
    print("  Enchan chooses tools when local evidence helps. Common tools include read_document, search_pattern, replace_text, write_text_file, and execute_command.")


def handle_cli_command(
    user_input: str,
    chat_history: list[dict],
    file_context: str,
    loaded_files: list[str],
    generation_config: dict,
    model=None,
    session_log_path: Path | None = None,
    agent_mode: bool = False,
    memory_recorder=None,
    tokenizer=None,
):
    parts = user_input.strip().split()
    command = parts[0].lower()
    model_id = model.config._name_or_path if model is not None and hasattr(model, "config") else generation_config.get("model_id", "ollama")
    enchan_config = getattr(model, "enchan_config", {}) if model is not None else {}


    if command == "/delegate":
        delegate_parts = user_input.strip().split(maxsplit=2)
        if len(delegate_parts) < 3:
            print("[Error] Usage: /delegate <codex|gemini|claude> <task prompt>")
            return True, file_context, False
        agent_name = delegate_parts[1].lower()
        prompt = delegate_parts[2]
        try:
            from agent_tools import execute_agent_tool
            result = execute_agent_tool({"tool": "delegate_agent", "args": {"agent": agent_name, "prompt": prompt}})
        except Exception as e:
            print(f"[Error] Delegation failed: {e}")
            return True, file_context, False
        observation = result.get("observation", "")
        ok = result.get("ok", False)
        print(f"\n[Delegate:{agent_name}] {'OK' if ok else 'FAILED'}")
        if observation:
            print(observation)
        append_session_event(
            session_log_path,
            {"type": "delegate_agent", "agent": agent_name, "ok": ok, "observation": observation[:4000]},
        )
        return True, file_context, False
    if command == "/model":
        if len(parts) > 2 or (len(parts) == 2 and looks_like_natural_language_arg(parts[1])):
            return False, file_context, False
        backend_mode = generation_config.get("backend", "enchan")
        if backend_mode not in ("ollama", "enchan"):
            print("[Error] /model command is only available in Ollama or Enchan modes.")
            return True, file_context, False
        
        host = generation_config.get("ollama_host", "http://localhost:11434")
        try:
            url = host.rstrip("/") + "/api/tags"
            with urllib.request.urlopen(url, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m["name"] for m in data.get("models", [])]
        except Exception as e:
            models = []
            try:
                manifest_root = Path.home() / ".ollama" / "models" / "manifests" / "registry.ollama.ai" / "library"
                if manifest_root.exists():
                    for model_dir in manifest_root.iterdir():
                        if model_dir.is_dir():
                            for tag_file in model_dir.iterdir():
                                if tag_file.is_file():
                                    models.append(f"{model_dir.name}:{tag_file.name}")
            except Exception:
                pass

            if not models:
                print(f"[Error] Failed to fetch Ollama models (and local manifest fallback failed): {e}")
                return True, file_context, False
        
        if not models:
            print("[System] No models found installed in Ollama.")
            return True, file_context, False
            
        current_model = generation_config.get("ollama_model")
        selected_model = None
        if len(parts) == 1:
            default_idx = 0
            options = []
            for i, model_name in enumerate(models):
                is_current = model_name == current_model or model_name.split(":")[0] == current_model
                if is_current:
                    default_idx = i
                desc = "current" if is_current else "available"
                options.append((model_name, desc, True))

            selected_idx = interactive_menu(f"Installed Ollama Models (Backend: {backend_mode})", options, default_idx=default_idx)
            if selected_idx < 0:
                print("[System] Switch cancelled.")
                return True, file_context, False
            selected_model = models[selected_idx]
        else:
            target = parts[1]
            if target.isdigit():
                idx = int(target) - 1
                if 0 <= idx < len(models):
                    selected_model = models[idx]
                else:
                    print(f"[Error] Invalid model number: {target}")
                    return True, file_context, False
            else:
                matched = [m for m in models if target in m]
                if matched:
                    selected_model = matched[0]
                else:
                    print(f"[Error] Model '{target}' not found in installed list.")
                    return True, file_context, False
        if selected_model:
            generation_config["ollama_model"] = selected_model
            generation_config["model_id"] = f"{backend_mode}:{selected_model}"
            print(f"[System] Switched active model to: {selected_model}")

            if backend_mode == "enchan":
                from enchan_llama_backend import shutdown_enchan_llama
                shutdown_enchan_llama()
                print("[System] Enchan Llama will load the selected model on the next prompt.")

            # Save this to enchan_config.json to persist!
            local_cfg = load_local_config()
            local_cfg["ollama_model"] = selected_model
            if backend_mode == "enchan":
                local_cfg["gguf_model"] = selected_model
            local_cfg["backend"] = backend_mode
            save_local_config(local_cfg)
            print("[System] Default model setting saved to enchan_config.json")
            
            # Sync generation parameter states based on model Modelfile recommendations + user JSON overrides
            sync_generation_config_to_active_model(generation_config, selected_model, backend_mode)
            
        return True, file_context, False

    if command == "/help":
        print_cli_help()
        return True, file_context, False

    if command == "/new":
        chat_history.clear()
        file_context = ""
        loaded_files.clear()
        append_session_event(session_log_path, {"type": "command", "command": "/new"})
        print("[System] New session started. (Chat history and file contexts cleared)")
        return True, file_context, False

    if command == "/status":
        print("\n[Status]")
        print(f"  Model: {model_id}")
        print(f"  Backend: {generation_config.get('backend', 'enchan')}")
        print(f"  Session log: {session_log_path}")
        print(f"  Chat history messages: {len(chat_history)}")
        print(f"  Pending file context chars: {len(file_context)}")
        print(f"  Last loaded files: {len(loaded_files)}")
        print(f"  max_input_tokens: {generation_config['max_input_tokens']}")
        print(f"  max_new_tokens: {generation_config['max_new_tokens']}")
        print(f"  temperature: {generation_config['temperature']}")
        print(f"  top_p: {generation_config['top_p']}")
        if enchan_config:
            print(f"  early_exit_threshold: {enchan_config.get('early_exit_threshold', 0.15)}")
            print(f"  force_early_exit_layer: {enchan_config.get('force_early_exit_layer', -1)}")
        print(f"  agent_mode: {agent_mode}")
        print(f"  Agent tools: {'active; forced tool-aware mode' if agent_mode else 'available; Enchan chooses when local evidence is needed'}")
        print(f"  Esc cancellation: enabled")
        return True, file_context, False

    if command == "/resume":
        if len(parts) > 2 or (len(parts) == 2 and looks_like_natural_language_arg(parts[1])):
            return False, file_context, False
        if len(parts) == 1:
            logs = list_session_logs(current_log_path=session_log_path, limit=10)
            if not logs:
                print("[System] No previous session logs found to resume.")
                return True, file_context, False

            options = []
            for path in logs:
                meta = get_session_metadata(path)
                label = f"{meta['last_active']} | {meta['turns']:2d} turns"
                options.append((label, meta["preview"], True))

            selected_idx = interactive_menu("Resumable Saved Sessions", options)
            if selected_idx < 0:
                print("[System] Cancelled.")
                return True, file_context, False
            log_path = logs[selected_idx]
        else:
            ref = parts[1]
            log_path = resolve_session_log(ref, current_log_path=session_log_path)
        if log_path is None:
            print(f"[Error] Session log not found (or invalid index): {ref}")
            return True, file_context, False
        messages = load_session_messages(log_path)
        if not messages:
            print(f"[Error] Session log has no resumable messages: {log_path.name}")
            return True, file_context, False
        chat_history[:] = messages
        file_context = ""
        loaded_files.clear()
        append_session_event(
            session_log_path,
            {
                "type": "resume",
                "source_log": str(log_path),
                "messages_loaded": len(messages),
            },
        )
        print(f"[System] Resumed {len(messages)} messages from {log_path.name}")
        return True, file_context, False

    if command == "/compress":
        if not chat_history:
            print("[System] Chat history is empty. Nothing to compress.")
            return True, file_context, False
        from context_compression import compress_chat_history
        chat_history[:] = compress_chat_history(chat_history, tokenizer=tokenizer, keep_turns=2)
        print("[System] Context optimized.")
        return True, file_context, False

    if command == "/set":
        backend_mode = generation_config.get("backend", "enchan")
        if len(parts) == 1:
            print("\n[Configurable Parameters]")
            print(f"  temp             = {generation_config.get('temperature', 1.0)} (sampling temperature)")
            print(f"  top_p            = {generation_config.get('top_p', 0.95)}")
            print(f"  top_k            = {generation_config.get('top_k', 64)}")
            print(f"  presence         = {generation_config.get('presence_penalty', 1.5)} (presence penalty)")
            print(f"  yarn             = {generation_config.get('yarn_factor', 1.0)} (YaRN scaling factor)")
            print(f"  max              = {generation_config.get('max_new_tokens', -1)} (max_new_tokens)")
            print(f"  input            = {generation_config.get('max_input_tokens', 131072)} (max_input_tokens)")
            if enchan_config:
                print(f"  exit_layer       = {enchan_config.get('force_early_exit_layer', -1)}")
                print(f"  exit_thresh      = {enchan_config.get('early_exit_threshold', 0.15)}")
            
            # Interactive in-place prompting for parameter changes
            change_input = styled_input("\nSelect parameter and value to change (e.g. 'temp 0.5', 'reset' to clear, or Enter to cancel): ")
            if not change_input:
                print("[System] No changes made.")
                return True, file_context, False
            change_parts = change_input.split()
            if len(change_parts) == 1 and change_parts[0].lower() in ("reset", "clear"):
                parts = ["/set", change_parts[0].lower()]
            elif len(change_parts) == 2:
                parts = ["/set", change_parts[0], change_parts[1]]
            else:
                print("[Error] Invalid format. Use 'temp 0.5', 'reset' to clear, or Enter to cancel.")
                return True, file_context, False

        # Intercept reset/clear commands before applying the 3-argument validation
        if len(parts) == 2 and parts[1].lower() in ("reset", "clear"):
            local_cfg = load_local_config()
            keys_to_remove = ["temperature", "top_p", "top_k", "presence_penalty", "max_new_tokens", "ollama_ctx", "view_think", "yarn_factor"]
            removed_any = False
            for k in keys_to_remove:
                if k in local_cfg:
                    del local_cfg[k]
                    removed_any = True
            if removed_any:
                save_local_config(local_cfg)
            
            # Reset active runtime parameters to dynamically loaded model recommended defaults!
            active_model = generation_config.get("gguf_model") if backend_mode == "enchan" else generation_config.get("ollama_model")
            sync_generation_config_to_active_model(generation_config, active_model, backend_mode)
            
            print("[System] Configuration overrides cleared. Reset to factory and model-specific recommended defaults.")
            return True, file_context, False

        if len(parts) != 3:
            print("[Error] Usage: /set <parameter> <value> (e.g. /set temp 0.7) or /set reset")
            return True, file_context, False
        key = parts[1].lower()
        value = parts[2]
        try:
            if key in ("temp", "temperature"):
                temperature = float(value)
                if temperature < 0.0 or temperature > 2.0:
                    raise ValueError("temperature must be between 0.0 and 2.0")
                generation_config["temperature"] = temperature
                print(f"[System] temperature = {temperature}")
            elif key == "top_p":
                top_p = float(value)
                if top_p <= 0.0 or top_p > 1.0:
                    raise ValueError("top_p must be greater than 0.0 and at most 1.0")
                generation_config["top_p"] = top_p
                print(f"[System] top_p = {top_p}")
            elif key == "top_k":
                top_k = int(value)
                if top_k < 1:
                    raise ValueError("top_k must be at least 1")
                generation_config["top_k"] = top_k
                print(f"[System] top_k = {top_k}")
            elif key in ("max", "max_new_tokens", "tokens"):
                max_tokens = int(value)
                if max_tokens < -1 or max_tokens == 0 or max_tokens > 32768:
                    raise ValueError("max_new_tokens must be -1 (infinite) or between 1 and 32768")
                generation_config["max_new_tokens"] = max_tokens
                print(f"[System] max_new_tokens = {max_tokens}")
            elif key in ("input", "max_input", "max_input_tokens"):
                max_input_tokens = int(value)
                if max_input_tokens < 512 or max_input_tokens > 262144:
                    raise ValueError("max_input_tokens must be between 512 and 262144")
                generation_config["max_input_tokens"] = max_input_tokens
                print(f"[System] max_input_tokens = {max_input_tokens}")
            elif key in ("exit_layer", "early_exit_layer"):
                if model is None:
                    raise ValueError("early exit settings are only available with --backend hf")
                layer = int(value)
                if layer < -1 or layer >= 42:
                    raise ValueError("early_exit_layer must be between -1 and 41")
                enchan_config["force_early_exit_layer"] = layer
                state = getattr(model, "enchan_field_state", None)
                if state:
                    state.total_tokens = 0
                    state.total_skipped_mlps = 0
                print(f"[System] force_early_exit_layer = {layer}")
            elif key in ("exit_thresh", "early_exit_threshold"):
                if model is None:
                    raise ValueError("early exit settings are only available with --backend hf")
                thresh = float(value)
                if thresh <= 0.0:
                    raise ValueError("early_exit_threshold must be positive")
                enchan_config["early_exit_threshold"] = thresh
                state = getattr(model, "enchan_field_state", None)
                if state:
                    state.total_tokens = 0
                    state.total_skipped_mlps = 0
                print(f"[System] early_exit_threshold = {thresh}")
            else:
                print("[Error] Unknown setting. Use temp, top_p, input, max, exit_layer, or exit_thresh.")
        except ValueError as e:
            print(f"[Error] {e}")
        
        # Persist updated parameters to enchan_config.json
        local_cfg = load_local_config()
        local_cfg["temperature"] = generation_config.get("temperature", 1.0)
        local_cfg["top_p"] = generation_config.get("top_p", 0.95)
        local_cfg["top_k"] = generation_config.get("top_k", 64)
        local_cfg["max_new_tokens"] = generation_config.get("max_new_tokens", -1)
        local_cfg["ollama_ctx"] = generation_config.get("max_input_tokens", 131072)
        local_cfg["think"] = generation_config.get("think", True)
        save_local_config(local_cfg)
        
        append_session_event(
            session_log_path,
            {
                "type": "command",
                "command": command,
                "generation_config": generation_config.copy(),
            },
        )
        return True, file_context, False

    if command in ("/exit", "/quit"):
        append_session_event(session_log_path, {"type": "session_end", "reason": command})
        if memory_recorder is not None:
            memory_recorder(command)
        print("Exiting...")
        return True, file_context, True

    print(f"[Error] Unknown command: {command}. Type /help for available commands.")
    return True, file_context, False

