from pathlib import Path
from backend.core import registry
from ui_theme import interactive_menu
from cli_commands import looks_like_natural_language_arg
from core.config import load_local_config, save_local_config
from runtime_config import sync_generation_config_to_active_model
from model_discovery import filter_enchan_gguf_models, list_installed_ollama_models

@registry.command("/model", desc="List or switch Ollama/Enchan models.", usage="/model [num|name]")
def handle_model(
    user_input: str,
    generation_config: dict,
    model=None,
    **kwargs
) -> tuple[bool, str, bool]:
    """Retrieves installed Ollama models, filters if Enchan, and swaps active inference engines."""
    parts = user_input.strip().split()
    file_context = kwargs.get("file_context", "")
    backend_mode = generation_config.get("backend", "enchan")
    
    if len(parts) > 2 or (len(parts) == 2 and looks_like_natural_language_arg(parts[1])):
        return False, file_context, False
        
    if backend_mode not in ("ollama", "enchan"):
        print("[Error] /model command is only available in Ollama or Enchan modes.")
        return True, file_context, False
        
    host = generation_config.get("ollama_host", "http://localhost:11434")
    models = list_installed_ollama_models(host)
    if backend_mode == "enchan":
        models = filter_enchan_gguf_models(models)
        
    if not models:
        if backend_mode == "enchan":
            print("[System] No GGUF models found installed in Ollama.")
        else:
            print("[System] No models found installed in Ollama.")
        return True, file_context, False
        
    current_model = generation_config.get("gguf_model") if backend_mode == "enchan" else generation_config.get("ollama_model")
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
