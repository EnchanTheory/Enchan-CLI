import argparse
import argparse
from pathlib import Path
from core.config import load_local_config
from ollama_backend import DEFAULT_OLLAMA_MODEL, DEFAULT_OLLAMA_HOST

def parse_args() -> argparse.Namespace:
    """Configures the ArgumentParser and parses CLI flags, merging with local_config overrides."""
    local_cfg = load_local_config()

    parser = argparse.ArgumentParser(description="Interactive Enchan CLI")
    default_backend = local_cfg.get("backend", "enchan")
    if default_backend not in {"ollama", "enchan"}:
        default_backend = "enchan"
        
    parser.add_argument("--backend", choices=["ollama", "enchan"], default=default_backend, help="runtime backend: ollama uses local Ollama; enchan uses Enchan Llama")
    parser.add_argument("--gguf-model", default="", help="path to GGUF model for --backend enchan (interactive startup shows a model picker when omitted)")
    parser.add_argument("--screen-strength", type=float, default=local_cfg.get("screen_strength", 0.2), help="screening strength for --backend enchan (default: 0.2)")
    parser.add_argument("--H-c", type=float, default=local_cfg.get("H_c", 1.6), help="scaling depth H_c for --backend enchan (default: 1.6)")
    parser.add_argument("--m", type=float, default=local_cfg.get("m", 1.5), help="sharpness power m for --backend enchan (default: 1.5)")
    parser.add_argument("--no-ram-guard", action="store_true", help="disable Enchan Llama system RAM reserve guard")
    parser.add_argument("--ram-reserve-ratio", type=float, default=local_cfg.get("ram_reserve_ratio", 0.05), help="fraction of physical RAM to keep free for --backend enchan (default: 0.05)")
    parser.add_argument("--ram-reserve-gb", type=float, default=local_cfg.get("ram_reserve_gb", 1.6), help="minimum GiB of physical RAM to keep free for --backend enchan (default: 1.6)")
    parser.add_argument("--ram-pressure-action", choices=["warn", "kill"], default=local_cfg.get("ram_pressure_action", "warn"), help="what to do when Enchan Llama crosses the RAM reserve (default: warn)")
    parser.add_argument("--llama-mmap", choices=["on", "off"], default=local_cfg.get("llama_mmap", "off"), help="memory-map GGUF model files for --backend enchan (default: off)")
    parser.add_argument("--llama-fit", action="store_true", default=local_cfg.get("llama_fit", False), help="enable llama.cpp --fit memory fitting for --backend enchan")
    parser.add_argument("--ollama-model", default=local_cfg.get("ollama_model", DEFAULT_OLLAMA_MODEL), help=f"Ollama model name for --backend ollama (default: {DEFAULT_OLLAMA_MODEL})")
    parser.add_argument("--ollama-host", default=local_cfg.get("ollama_host", DEFAULT_OLLAMA_HOST), help=f"Ollama API host for --backend ollama (default: {DEFAULT_OLLAMA_HOST})")
    parser.add_argument("--ollama-ctx", type=int, default=local_cfg.get("ollama_ctx", 131072), help="Ollama num_ctx for --backend ollama/enchan (default: 131072)")
    parser.add_argument("--no-ollama-start", action="store_true", help="do not auto-start `ollama serve` when --backend ollama cannot reach the API")
    parser.add_argument("--view-think", action="store_true", default=local_cfg.get("view_think", False), help="show model thinking traces")
    parser.add_argument("--max-new-tokens", type=int, default=local_cfg.get("max_new_tokens", -1), help="maximum generated tokens for --backend ollama (-1 for infinite)")
    parser.add_argument("--temperature", type=float, default=local_cfg.get("temperature", 1.0), help="sampling temperature for --backend ollama (default: 1.0)")
    parser.add_argument("--top-p", type=float, default=local_cfg.get("top_p", 0.95), help="top_p for --backend ollama (default: 0.95)")
    parser.add_argument("--top-k", type=int, default=local_cfg.get("top_k", 64), help="top_k for --backend ollama (default: 64)")
    parser.add_argument("--presence-penalty", type=float, default=local_cfg.get("presence_penalty", 0.0), help="presence penalty for --backend ollama/enchan (default: 0.0)")
    parser.add_argument("--no-thinking", action="store_true", help="Disable thinking mode (Qwen3.6)")
    parser.add_argument("--preserve-thinking", action="store_true", help="Preserve thinking history in chat context (Qwen3.6)")
    parser.add_argument("--text-only", action="store_true", help="Text-only mode (skip vision encoder for Qwen3.6)")
    parser.add_argument("--mtp", action="store_true", help="Enable Multi-Token Prediction (Qwen3.6 MTP)")
    parser.add_argument("--yarn-factor", type=float, default=local_cfg.get("yarn_factor", 1.0), help="YaRN scaling factor for ultra-long context (e.g., 4.0 for >256K)")
    parser.add_argument("--ask", help="run one non-interactive prompt and exit; intended for local agent delegation")
    parser.add_argument("--ask-file", help="read one non-interactive prompt from a UTF-8 file and exit")
    parser.add_argument("--plain", action="store_true", help="with --ask/--ask-file, print only the final assistant response")
    parser.add_argument("--agent", action="store_true", help="enable deterministic ReAct tool execution mode")
    
    args = parser.parse_args()
    
    if args.ask and args.ask_file:
        parser.error("--ask and --ask-file cannot be used together")
        
    return args
