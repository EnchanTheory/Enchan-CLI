import json
from pathlib import Path
from dataclasses import dataclass, field, asdict, fields
from typing import Any, Dict, Optional

# Path resolution for local config
CORE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CORE_DIR.parent
CLI_DIR = BACKEND_DIR.parent

@dataclass
class EnchanConfig:
    # Backend settings
    backend: str = "enchan"
    gguf_model: str = ""
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e2b-it-qat"
    ollama_ctx: int = 131072
    
    # Generation parameters
    temperature: float = 1.0
    top_p: float = 0.95
    top_k: int = 64
    max_new_tokens: int = -1
    presence_penalty: float = 0.0
    
    # Enchan (llama-server) specific parameters
    screen_strength: float = 0.2
    H_c: float = 1.6
    m: float = 1.5
    ram_reserve_ratio: float = 0.05
    ram_reserve_gb: float = 1.6
    ram_pressure_action: str = "warn"
    llama_mmap: str = "off"
    llama_fit: bool = False
    yarn_factor: float = 1.0
    
    # UI and tracing options
    view_think: bool = False
    screen_width: int = 100
    
    # For any custom or extra keys that aren't explicitly declared
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, file_path: Optional[Path] = None) -> "EnchanConfig":
        """Loads and parses the config JSON, parsing it into a type-safe Dataclass."""
        path = file_path or (CLI_DIR / "enchan_config.json")
        if not path.exists():
            return cls()
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            # Safe fallback if JSON parsing fails
            print(f"[Warning] Failed to read/parse config from {path}: {e}")
            return cls()
            
        # Class fields partition
        allowed_keys = {f.name for f in fields(cls)}
        kwargs = {}
        extra = {}
        
        for k, v in data.items():
            if k in allowed_keys:
                kwargs[k] = v
            else:
                extra[k] = v
                
        return cls(**kwargs, extra=extra)

    def save(self, file_path: Optional[Path] = None):
        """Serializes current state and merges extra fields back to disk safely."""
        path = file_path or (CLI_DIR / "enchan_config.json")
        data = asdict(self)
        
        # Merge extra properties back so we don't accidentally wipe out user-defined values
        extra = data.pop("extra", {})
        data.update(extra)
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Warning] Failed to write config to {path}: {e}")
