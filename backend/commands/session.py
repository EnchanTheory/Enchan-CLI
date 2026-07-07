from pathlib import Path
from backend.core import registry
from backend.ui_theme import interactive_menu, styled_input
from backend.session_log import (
    append_session_event,
    list_session_logs,
    load_session_messages,
    resolve_session_log,
    get_session_metadata,
)

# Note: Core config and runtime utilities imported from the new dedicated modules
from backend.core.config import load_local_config, save_local_config
from backend.runtime_config import sync_generation_config_to_active_model
from backend.kv_cache_config import VALID_KV_CACHE_TYPES, apply_enchan_kv_cache_patch, normalize_kv_cache_type

@registry.command("/new", desc="Start a new session and clear current context.")
def handle_new(
    chat_history: list[dict],
    loaded_files: list[str],
    session_log_path: Path | None = None,
    **kwargs
) -> tuple[bool, str, bool]:
    """Clears active session conversation history and file contexts."""
    chat_history.clear()
    loaded_files.clear()
    append_session_event(session_log_path, {"type": "command", "command": "/new"})
    print("[System] New session started. (Chat history and file contexts cleared)")
    return True, "", False


@registry.command("/resume", desc="Resume a saved session.", usage="/resume [num|name]")
def handle_resume(
    user_input: str,
    chat_history: list[dict],
    loaded_files: list[str],
    session_log_path: Path | None = None,
    **kwargs
) -> tuple[bool, str, bool]:
    """Loads a previously recorded session history into active memory."""
    parts = user_input.strip().split()
    file_context = kwargs.get("file_context", "")
    
    if len(parts) > 2:
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
        print(f"[Error] Session log not found (or invalid index)")
        return True, file_context, False
        
    messages = load_session_messages(log_path)
    if not messages:
        print(f"[Error] Session log has no resumable messages: {log_path.name}")
        return True, file_context, False
        
    chat_history[:] = messages
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
    return True, "", False


@registry.command("/compress", desc="Optimize older conversation turns invisibly.")
def handle_compress(
    chat_history: list[dict],
    tokenizer=None,
    **kwargs
) -> tuple[bool, str, bool]:
    """Compresses oldest turns in active conversation using Context Compression middleware."""
    file_context = kwargs.get("file_context", "")
    if not chat_history:
        print("[System] Chat history is empty. Nothing to compress.")
        return True, file_context, False
        
    from backend.context_compression import compress_chat_history
    chat_history[:] = compress_chat_history(chat_history, tokenizer=tokenizer, keep_turns=2)
    print("[System] Context optimized.")
    return True, file_context, False


@registry.command("/set", desc="Show or change generation settings interactively.", usage="/set <parameter> <value> or /set reset")
def handle_set(
    user_input: str,
    generation_config: dict,
    model=None,
    session_log_path: Path | None = None,
    **kwargs
) -> tuple[bool, str, bool]:
    """Provides interactive parameters setup and allows live overriding generation values."""
    parts = user_input.strip().split()
    file_context = kwargs.get("file_context", "")
    backend_mode = generation_config.get("backend", "enchan")
    enchan_config = getattr(model, "enchan_config", {}) if model is not None else {}
    args = kwargs.get("args")
    
    if len(parts) == 1:
        print("\n[Configurable Parameters]")
        print(f"  temperature      = {generation_config.get('temperature', 1.0)} (sampling temperature)")
        print(f"  top_p            = {generation_config.get('top_p', 0.95)}")
        print(f"  top_k            = {generation_config.get('top_k', 64)}")
        print(f"  presence         = {generation_config.get('presence_penalty', 1.5)} (presence penalty)")
        print(f"  yarn             = {generation_config.get('yarn_factor', 1.0)} (YaRN scaling factor)")
        print(f"  max              = {generation_config.get('max_new_tokens', -1)} (max_new_tokens)")
        print(f"  input            = {generation_config.get('max_input_tokens', 131072)} (max_input_tokens)")
        print(f"  obs_chars        = {load_local_config().get('max_obs_chars', 10000)} (max tool output chars)")
        print(f"  dynatemp_range   = {generation_config.get('dynatemp_range', 0.0)} (dynamic temperature range)")
        print(f"  mirostat         = {generation_config.get('mirostat', 0)} (Mirostat mode: 0, 1, 2)")
        print(f"  mirostat_lr      = {generation_config.get('mirostat_lr', 0.1)} (Mirostat learning rate)")
        print(f"  mirostat_ent     = {generation_config.get('mirostat_ent', 5.0)} (Mirostat target entropy)")
        if backend_mode == "enchan":
            print(f"  screen_strength  = {generation_config.get('screen_strength', getattr(args, 'screen_strength', 0.2))} (Enchan screening strength)")
            print(f"  kv_cache_type    = {generation_config.get('kv_cache_type', getattr(args, 'kv_cache_type', 'q4_0'))} (Enchan KV cache dtype)")
        if enchan_config:
            print(f"  exit_layer       = {enchan_config.get('force_early_exit_layer', -1)}")
            print(f"  exit_thresh      = {enchan_config.get('early_exit_threshold', 0.15)}")
        
        change_input = styled_input("\nSelect parameter and value to change (e.g. 'screen_strength 0.4', 'reset' to clear, or Enter to cancel): ")
        if not change_input:
            print("[System] No changes made.")
            return True, file_context, False
        change_parts = change_input.split()
        if len(change_parts) == 1 and change_parts[0].lower() in ("reset", "clear"):
            parts = ["/set", change_parts[0].lower()]
        elif len(change_parts) == 2:
            parts = ["/set", change_parts[0], change_parts[1]]
        else:
            print("[Error] Invalid format. Use 'screen_strength 0.4', 'reset' to clear, or Enter to cancel.")
            return True, file_context, False

    # Reset command intercept
    if len(parts) == 2 and parts[1].lower() in ("reset", "clear"):
        local_cfg = load_local_config()
        keys_to_remove = ["temperature", "top_p", "top_k", "presence_penalty", "max_new_tokens", "ollama_ctx", "view_think", "yarn_factor", "dynatemp_range", "mirostat", "mirostat_lr", "mirostat_ent", "screen_strength", "kv_cache_type"]
        removed_any = False
        for k in keys_to_remove:
            if k in local_cfg:
                del local_cfg[k]
                removed_any = True
        if removed_any:
            save_local_config(local_cfg)
        
        active_model = generation_config.get("gguf_model") if backend_mode == "enchan" else generation_config.get("ollama_model")
        sync_generation_config_to_active_model(generation_config, active_model, backend_mode)
        if backend_mode == "enchan":
            generation_config["screen_strength"] = getattr(args, "screen_strength", 0.2)
            generation_config["kv_cache_type"] = normalize_kv_cache_type(getattr(args, "kv_cache_type", None))
        
        print("[System] Configuration overrides cleared. Reset to factory and model-specific recommended defaults.")
        return True, file_context, False

    if len(parts) != 3:
        print("[Error] Usage: /set <parameter> <value> (e.g. /set screen_strength 0.4) or /set reset")
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
        elif key in ("obs", "obs_chars", "max_obs_chars"):
            obs_chars = int(value)
            if obs_chars < 1000 or obs_chars > 200000:
                raise ValueError("max_obs_chars must be between 1000 and 200000")
            generation_config["max_obs_chars"] = obs_chars
            print(f"[System] max_obs_chars = {obs_chars}")
        elif key in ("dynatemp", "dynatemp_range", "dynatemp-range"):
            dynatemp = float(value)
            if dynatemp < 0.0 or dynatemp > 2.0:
                raise ValueError("dynatemp_range must be between 0.0 and 2.0")
            generation_config["dynatemp_range"] = dynatemp
            print(f"[System] dynatemp_range = {dynatemp}")
        elif key == "mirostat":
            mirostat = int(value)
            if mirostat not in (0, 1, 2):
                raise ValueError("mirostat must be 0 (disabled), 1, or 2")
            generation_config["mirostat"] = mirostat
            print(f"[System] mirostat = {mirostat}")
        elif key in ("mirostat_lr", "mirostat-lr"):
            mirostat_lr = float(value)
            if mirostat_lr <= 0.0 or mirostat_lr > 1.0:
                raise ValueError("mirostat_lr must be between 0.0 and 1.0")
            generation_config["mirostat_lr"] = mirostat_lr
            print(f"[System] mirostat_lr = {mirostat_lr}")
        elif key in ("mirostat_ent", "mirostat-ent"):
            mirostat_ent = float(value)
            if mirostat_ent <= 0.0:
                raise ValueError("mirostat_ent must be positive")
            generation_config["mirostat_ent"] = mirostat_ent
            print(f"[System] mirostat_ent = {mirostat_ent}")
        elif key == "screen_strength":
            screen_strength = float(value)
            if screen_strength < 0.0 or screen_strength > 2.0:
                raise ValueError("screen_strength must be between 0.0 and 2.0")
            generation_config["screen_strength"] = screen_strength
            if args is not None:
                args.screen_strength = screen_strength
            print(f"[System] screen_strength = {screen_strength}")
            if backend_mode == "enchan":
                from backend.enchan_llama_backend import shutdown_enchan_llama
                shutdown_enchan_llama()
                print("[System] Enchan engine will restart with the new screen_strength on the next request.")
        elif key == "kv_cache_type":
            kv_type = value.strip().lower()
            if kv_type not in VALID_KV_CACHE_TYPES:
                raise ValueError("kv_cache_type must be one of: q4_0, q8_0, f16")
            generation_config["kv_cache_type"] = kv_type
            if args is not None:
                args.kv_cache_type = kv_type
            if backend_mode == "enchan":
                apply_enchan_kv_cache_patch(kv_type)
                from backend.enchan_llama_backend import shutdown_enchan_llama
                shutdown_enchan_llama()
                print("[System] Enchan engine will restart with the new kv_cache_type on the next request.")
            print(f"[System] kv_cache_type = {kv_type}")
        else:
            print("[Error] Unknown setting. Use temperature, top_p, top_k, max_input_tokens, max_new_tokens, obs_chars, dynatemp_range, mirostat, mirostat_lr, mirostat_ent, screen_strength, or kv_cache_type.")
    except ValueError as e:
        print(f"[Error] {e}")
        return True, file_context, False
        
    # Persist updated parameters to enchan_config.json
    local_cfg = load_local_config()
    local_cfg["temperature"] = generation_config.get("temperature", 1.0)
    local_cfg["top_p"] = generation_config.get("top_p", 0.95)
    local_cfg["top_k"] = generation_config.get("top_k", 64)
    local_cfg["max_new_tokens"] = generation_config.get("max_new_tokens", -1)
    local_cfg["ollama_ctx"] = generation_config.get("max_input_tokens", 131072)
    local_cfg["max_obs_chars"] = generation_config.get("max_obs_chars", 10000)
    local_cfg["think"] = generation_config.get("think", True)
    if "dynatemp_range" in generation_config:
        local_cfg["dynatemp_range"] = generation_config["dynatemp_range"]
    if "mirostat" in generation_config:
        local_cfg["mirostat"] = generation_config["mirostat"]
    if "mirostat_lr" in generation_config:
        local_cfg["mirostat_lr"] = generation_config["mirostat_lr"]
    if "mirostat_ent" in generation_config:
        local_cfg["mirostat_ent"] = generation_config["mirostat_ent"]
    if "screen_strength" in generation_config:
        local_cfg["screen_strength"] = generation_config["screen_strength"]
    if "kv_cache_type" in generation_config:
        local_cfg["kv_cache_type"] = generation_config["kv_cache_type"]
    save_local_config(local_cfg)
    
    append_session_event(
        session_log_path,
        {
            "type": "command",
            "command": "/set",
            "generation_config": generation_config.copy(),
        },
    )
    return True, file_context, False


@registry.command("/exit", desc="Exit the CLI.")
@registry.command("/quit", desc="Exit the CLI.")
def handle_exit(
    user_input: str,
    session_log_path: Path | None = None,
    memory_recorder=None,
    **kwargs
) -> tuple[bool, str, bool]:
    """Ends the active chat session safely and shuts down the Enchan environment."""
    command = user_input.strip().split()[0].lower()
    file_context = kwargs.get("file_context", "")
    append_session_event(session_log_path, {"type": "session_end", "reason": command})
    if memory_recorder is not None:
        memory_recorder(command)
    print("Exiting...")
    return True, file_context, True
