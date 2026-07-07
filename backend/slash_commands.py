MAIN_SLASH_COMMANDS = (
    ("/resume", "List resumable sessions or resume a specific session", None),
    ("/compress", "Optimize older conversation turns", None),
    ("/model", "Switch the active model", None),
    ("/status", "Show model, history, context, and generation settings", None),
    ("/set", "Configure generation and early exit parameters", {
        "temperature": ("Set sampling temperature, e.g., /set temperature 0.7", None),
        "top_p": ("Set nucleus sampling threshold, e.g., /set top_p 0.95", None),
        "top_k": ("Set top_k sampling count, e.g., /set top_k 40", None),
        "presence": ("Set presence penalty, e.g., /set presence 1.5", None),
        "yarn": ("Set YaRN scaling factor, e.g., /set yarn 1.0", None),
        "max": ("Set max generated tokens (-1 for infinite)", None),
        "input": ("Set max input context tokens allowed", None),
        "obs_chars": ("Set max tool output chars, e.g., /set obs_chars 10000", None),
        "dynatemp_range": ("Set dynamic temperature range, e.g., /set dynatemp_range 0.0", None),
        "mirostat": ("Set Mirostat mode: 0, 1, 2, e.g., /set mirostat 0", None),
        "mirostat_lr": ("Set Mirostat learning rate, e.g., /set mirostat_lr 0.1", None),
        "mirostat_ent": ("Set Mirostat target entropy, e.g., /set mirostat_ent 5.0", None),
        "screen_strength": ("Set Enchan screening strength, e.g., /set screen_strength 0.2", None),
        "kv_cache_type": ("Set Enchan KV cache dtype, e.g., /set kv_cache_type q4_0", None),
        "exit_layer": ("Set force early exit layer index (HF only)", None),
        "exit_thresh": ("Set early exit threshold probability (HF only)", None),
        "reset": ("Reset all generation parameters to defaults", None),
    }),
    ("/llama_set", "Configure unmanaged raw llama-server passthrough args", {
        "reset": ("Reset all unmanaged llama-server args", None),
    }),
    ("/new", "Start a new session (clears chat history and file context)", None),
    ("/exit", "Exit the CLI", None),
    ("/help", "Show help menu and available commands", None),
    ("/license", "Show repository license terms", None),
)

COMMAND_COMPLETIONS = {
    command: (description, subcommands)
    for command, description, subcommands in MAIN_SLASH_COMMANDS
}

MAIN_SLASH_COMMAND_NAMES = tuple(command for command, _, _ in MAIN_SLASH_COMMANDS)
KNOWN_SLASH_COMMANDS = frozenset(MAIN_SLASH_COMMAND_NAMES + ("/quit", "/delegate"))
