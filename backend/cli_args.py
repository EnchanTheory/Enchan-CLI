import argparse
from pathlib import Path
from backend.core.config import EnchanConfig
from backend.ollama_backend import DEFAULT_OLLAMA_MODEL, DEFAULT_OLLAMA_HOST
from backend.kv_cache_config import DEFAULT_KV_CACHE_TYPE, VALID_KV_CACHE_TYPES
from backend.llama_args import normalize_llama_extra_args


def parse_args() -> argparse.Namespace:
    """Configures the ArgumentParser and parses CLI flags, merging with local_config overrides."""
    cfg = EnchanConfig.load()

    parser = argparse.ArgumentParser(description="Interactive Enchan CLI")
    default_backend = cfg.backend
    if default_backend not in {"ollama", "enchan"}:
        default_backend = "enchan"

    parser.add_argument("--backend", choices=["ollama", "enchan"], default=default_backend, help="runtime backend: ollama uses local Ollama; enchan uses Enchan Llama")
    parser.add_argument("--gguf-model", default="", help="path to GGUF model for --backend enchan (interactive startup shows a model picker when omitted)")
    parser.add_argument("--screen-strength", type=float, default=cfg.screen_strength, help="screening strength for --backend enchan (default: 0.2)")
    parser.add_argument("--H-c", type=float, default=cfg.H_c, help="scaling depth H_c for --backend enchan (default: 1.6)")
    parser.add_argument("--m", type=float, default=cfg.m, help="sharpness power m for --backend enchan (default: 1.5)")
    parser.add_argument("--no-ram-guard", action="store_true", help="disable Enchan Llama system RAM reserve guard")
    parser.add_argument("--ram-reserve-ratio", type=float, default=cfg.ram_reserve_ratio, help="fraction of physical RAM to keep free for --backend enchan (default: 0.05)")
    parser.add_argument("--ram-reserve-gb", type=float, default=cfg.ram_reserve_gb, help="minimum GiB of physical RAM to keep free for --backend enchan (default: 1.6)")
    parser.add_argument("--ram-pressure-action", choices=["warn", "kill"], default=cfg.ram_pressure_action, help="what to do when Enchan Llama crosses the RAM reserve (default: warn)")
    parser.add_argument("--llama-mmap", choices=["on", "off"], default=cfg.llama_mmap, help="memory-map GGUF model files for --backend enchan (default: off)")
    parser.add_argument("--llama-fit", action="store_true", default=cfg.llama_fit, help="enable llama.cpp --fit memory fitting for --backend enchan")
    parser.add_argument("--kv-cache-type", choices=sorted(VALID_KV_CACHE_TYPES), default=getattr(cfg, "kv_cache_type", DEFAULT_KV_CACHE_TYPE), help="KV cache dtype for --backend enchan (default: q4_0; choices: q4_0, q8_0, f16)")
    parser.add_argument("--llama-arg", action="append", default=list(getattr(cfg, "llama_extra_args", [])), help="append a raw unmanaged llama-server argument; repeat for multiple args")
    parser.add_argument("--ollama-model", default=cfg.ollama_model, help=f"Ollama model name for --backend ollama (default: {DEFAULT_OLLAMA_MODEL})")
    parser.add_argument("--ollama-host", default=cfg.ollama_host, help=f"Ollama API host for --backend ollama (default: {DEFAULT_OLLAMA_HOST})")
    parser.add_argument("--ollama-ctx", type=int, default=cfg.ollama_ctx, help="Ollama num_ctx for --backend ollama/enchan (default: 131072)")
    parser.add_argument("--no-ollama-start", action="store_true", help="do not auto-start `ollama serve` when --backend ollama cannot reach the API")
    parser.add_argument("--view-think", action="store_true", default=cfg.view_think, help="show model thinking traces")
    parser.add_argument("--max-new-tokens", type=int, default=cfg.max_new_tokens, help="maximum generated tokens for --backend ollama (-1 for infinite)")
    parser.add_argument("--temperature", type=float, default=cfg.temperature, help="sampling temperature for --backend ollama (default: 1.0)")
    parser.add_argument("--top-p", type=float, default=cfg.top_p, help="top_p for --backend ollama (default: 0.95)")
    parser.add_argument("--top-k", type=int, default=cfg.top_k, help="top_k for --backend ollama (default: 64)")
    parser.add_argument("--presence-penalty", type=float, default=cfg.presence_penalty, help="presence penalty for --backend ollama/enchan (default: 0.0)")
    parser.add_argument("--no-thinking", action="store_true", help="Disable thinking mode (Qwen3.6)")
    parser.add_argument("--preserve-thinking", action="store_true", help="Preserve thinking history in chat context (Qwen3.6)")
    parser.add_argument("--text-only", action="store_true", help="Text-only mode (skip vision encoder for Qwen3.6)")
    parser.add_argument("--mtp", action="store_true", help="Enable Multi-Token Prediction (Qwen3.6 MTP)")
    parser.add_argument("--yarn-factor", type=float, default=cfg.yarn_factor, help="YaRN scaling factor for ultra-long context (e.g., 4.0 for >256K)")
    parser.add_argument("--ask", help="run one non-interactive prompt and exit; intended for local agent delegation")
    parser.add_argument("--ask-file", help="read one non-interactive prompt from a UTF-8 file and exit")
    parser.add_argument("--plain", action="store_true", help="with --ask/--ask-file, print only the final assistant response")
    parser.add_argument("--agent", action="store_true", help="enable deterministic ReAct tool execution mode")

    args = parser.parse_args()

    if args.ask and args.ask_file:
        parser.error("--ask and --ask-file cannot be used together")

    # Detect which generation parameters were explicitly passed on the command line
    parser_detect = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    parser_detect.add_argument("--temperature", type=float)
    parser_detect.add_argument("--top-p", type=float)
    parser_detect.add_argument("--top-k", type=int)
    parser_detect.add_argument("--presence-penalty", type=float)
    parser_detect.add_argument("--yarn-factor", type=float)
    parser_detect.add_argument("--max-new-tokens", type=int)
    parser_detect.add_argument("--ollama-ctx", type=int)
    parser_detect.add_argument("--kv-cache-type")
    parser_detect.add_argument("--llama-arg", action="append")

    explicit_ns, _ = parser_detect.parse_known_args()
    args.explicit_overrides = vars(explicit_ns)
    args.llama_arg = normalize_llama_extra_args(getattr(args, "llama_arg", []))

    return args
