import urllib.request
import json
from backend.core.config import load_local_config

def estimate_text_tokens_rough(text: str) -> int:
    """Estimates tokens in raw text dynamically. Handles CJK characters with higher weight."""
    if not text:
        return 0
    cjk_count = sum(
        1
        for ch in text
        if "\u3040" <= ch <= "\u30ff"
        or "\u3400" <= ch <= "\u4dbf"
        or "\u4e00" <= ch <= "\u9fff"
        or "\uf900" <= ch <= "\ufaff"
    )
    if cjk_count:
        return max(1, cjk_count + ((len(text) - cjk_count) // 4))
    return max(1, len(text) // 4)


def count_text_tokens(tokenizer, text: str) -> int:
    """Helper to return token count from a tokenizer instance."""
    if tokenizer is None or not text:
        return 0
    return len(tokenizer.encode(text, add_special_tokens=False))


class RunningModelTokenizer:
    """Lightweight bridge tokenizer that calls Ollama or llama-server API directly."""
    
    def __init__(self, backend_type: str = "", host: str = "", model_name: str = ""):
        self._backend_type = backend_type
        self._host = host
        self._model_name = model_name

    def _get_active_config(self) -> tuple[str, str, str]:
        # Dynamically fetch config to support hot-swapping models/backends in the same session!
        local_cfg = load_local_config()
        backend_mode = local_cfg.get("backend", self._backend_type or "enchan")
        
        if backend_mode == "enchan":
            host = "http://localhost:8080"
            model = local_cfg.get("gguf_model", self._model_name)
        else:
            host = local_cfg.get("ollama_host", self._host or "http://localhost:11434")
            model = local_cfg.get("ollama_model", self._model_name)
            
        return backend_mode, host, model

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        if not text:
            return []
        
        backend_mode, host, model = self._get_active_config()
        
        if backend_mode == "enchan":
            url = f"{host}/tokenize"
            payload = {"content": text}
        else:
            url = f"{host}/api/tokenize"
            payload = {"model": model, "prompt": text}
            
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("tokens", [])
        except Exception:
            # Fallback to local estimation
            return [0] * estimate_text_tokens_rough(text)

    def decode(self, token_ids: list[int], skip_special_tokens: bool = True) -> str:
        if not token_ids:
            return ""
        
        backend_mode, host, model = self._get_active_config()
        
        if backend_mode == "enchan":
            url = f"{host}/detokenize"
            payload = {"tokens": token_ids}
        else:
            url = f"{host}/api/detokenize"
            payload = {"model": model, "tokens": token_ids}
            
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("content", "") or data.get("prompt", "")
        except Exception:
            return f"[Detokenize Fallback: {len(token_ids)} tokens]"

    def apply_chat_template(self, messages: list[dict], add_generation_prompt: bool = True, tokenize: bool = False) -> str:
        _, _, model = self._get_active_config()
        name = str(model).lower()
        is_qwen = "qwen" in name
        is_llama = "llama" in name or "enchan" in name
        is_gemma = "gemma" in name or (not is_qwen and not is_llama)
        
        formatted = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "model":
                role = "assistant"
                
            if is_gemma:
                formatted += f"<start_of_turn>{role}\n{content}<end_of_turn>\n"
            elif is_qwen:
                formatted += f"<|im_start|>{role}\n{content}<|im_end|>\n"
            elif is_llama:
                formatted += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
                
        if add_generation_prompt:
            if is_gemma:
                formatted += "<start_of_turn>model\n"
            elif is_qwen:
                formatted += "<|im_start|>assistant\n"
            elif is_llama:
                formatted += "<|start_header_id|>assistant<|end_header_id|>\n\n"
                
        return formatted


def load_enchan_tokenizer_for_ollama(model_name: str = "") -> RunningModelTokenizer:
    """Interoperability factory to return the RunningModelTokenizer."""
    return RunningModelTokenizer()
