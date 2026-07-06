from backend.core.config import EnchanConfig

def sync_generation_config_to_active_model(generation_config: dict, active_model_name: str, backend_mode: str):
    """Loads official model recommendations, merges with user-set JSON overrides, and updates generation_config in-place."""
    local_cfg = EnchanConfig.load()

    # 1. Start with system baseline defaults
    default_params = {
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 40,
        "presence_penalty": 0.0,
        "yarn_factor": 1.0,
        "max_new_tokens": -1,
        "max_input_tokens": 131072,
        "dynatemp_range": 0.0,
        "mirostat": 0,
        "mirostat_lr": 0.1,
        "mirostat_ent": 5.0,
    }

    # 2. Try loading official recommended params from the Ollama Modelfile manifest
    if active_model_name and backend_mode in ("ollama", "enchan"):
        try:
            from backend.enchan_llama_backend import resolve_ollama_model_to_blob
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
                if "dynatemp_range" in official_params:
                    default_params["dynatemp_range"] = float(official_params["dynatemp_range"])
                if "mirostat" in official_params:
                    default_params["mirostat"] = int(official_params["mirostat"])
                if "mirostat_lr" in official_params:
                    default_params["mirostat_lr"] = float(official_params["mirostat_lr"])
                elif "mirostat_eta" in official_params:
                    default_params["mirostat_lr"] = float(official_params["mirostat_eta"])
                if "mirostat_ent" in official_params:
                    default_params["mirostat_ent"] = float(official_params["mirostat_ent"])
                elif "mirostat_tau" in official_params:
                    default_params["mirostat_ent"] = float(official_params["mirostat_tau"])
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
    if "dynatemp_range" in local_cfg:
        default_params["dynatemp_range"] = float(local_cfg["dynatemp_range"])
    if "mirostat" in local_cfg:
        default_params["mirostat"] = int(local_cfg["mirostat"])
    if "mirostat_lr" in local_cfg:
        default_params["mirostat_lr"] = float(local_cfg["mirostat_lr"])
    if "mirostat_ent" in local_cfg:
        default_params["mirostat_ent"] = float(local_cfg["mirostat_ent"])

    # 4. Synchronize all values back to the generation_config in-place
    generation_config["temperature"] = default_params["temperature"]
    generation_config["top_p"] = default_params["top_p"]
    generation_config["top_k"] = default_params["top_k"]
    generation_config["presence_penalty"] = default_params["presence_penalty"]
    generation_config["yarn_factor"] = default_params["yarn_factor"]
    generation_config["max_new_tokens"] = default_params["max_new_tokens"]
    generation_config["max_input_tokens"] = default_params["max_input_tokens"]
    generation_config["dynatemp_range"] = default_params["dynatemp_range"]
    generation_config["mirostat"] = default_params["mirostat"]
    generation_config["mirostat_lr"] = default_params["mirostat_lr"]
    generation_config["mirostat_ent"] = default_params["mirostat_ent"]
