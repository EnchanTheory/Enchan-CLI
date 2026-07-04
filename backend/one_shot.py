from pathlib import Path
from session_log import append_session_event
from memory_store import load_memory_context
from ollama_backend import run_ollama_once


def execute_single_turn(
    single_turn_prompt: str,
    backend_mode: str,
    session_log_path: Path,
    chat_history: list,
    generation_config: dict,
    args,
    tokenizer=None,
    plain_output: bool = False,
) -> None:
    """Executes a non-interactive one-shot turn using --ask/--ask-file and exits."""
    if backend_mode not in ("ollama", "enchan"):
        append_session_event(session_log_path, {"type": "error", "stage": "single_turn_backend", "backend": backend_mode})
        print("[Error] --ask and --ask-file currently require --backend ollama or --backend enchan.")
        return
        
    if not single_turn_prompt.strip():
        append_session_event(session_log_path, {"type": "error", "stage": "single_turn_empty_prompt"})
        print("[Error] --ask prompt is empty.")
        return

    if backend_mode == "enchan":
        from enchan_llama_backend import run_enchan_llama_once
        memory_context = load_memory_context()
        run_enchan_llama_once(
            single_turn_prompt.strip(),
            chat_history,
            generation_config,
            session_log_path,
            args,
            tokenizer=tokenizer,
            plain=plain_output,
            memory_context=memory_context,
        )
        append_session_event(session_log_path, {"type": "session_end", "reason": "single_turn"})
        return

    memory_context = load_memory_context()
    run_ollama_once(
        single_turn_prompt.strip(),
        chat_history,
        generation_config,
        session_log_path,
        args,
        tokenizer=tokenizer,
        plain=plain_output,
        memory_context=memory_context,
    )
    append_session_event(session_log_path, {"type": "session_end", "reason": "single_turn"})
