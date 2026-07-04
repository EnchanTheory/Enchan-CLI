import sys
import shutil
from typing import Optional

try:
    import msvcrt
except ImportError:
    msvcrt = None

from ui_theme import interactive_menu
from backend.ollama_registry import (
    list_installed_ollama_models,
    ENCHAN_DEFAULT_DOWNLOAD_MODEL,
    ENCHAN_DEFAULT_DOWNLOAD_SIZE,
)

def select_startup_backend(default_backend: str) -> str:
    """Interactively prompts the user to select the active execution backend (Enchan or Ollama)."""
    ollama_ready = shutil.which("ollama") is not None

    choices = [
        ("enchan", "Local: Enchan Llama", True),
        ("ollama", "Local: Ollama API chat", ollama_ready),
    ]

    valid_choices = {name for name, _, ready in choices if ready}
    default_backend = default_backend if default_backend in valid_choices else "enchan"
    
    current_idx = 0
    for i, (name, _, _) in enumerate(choices):
        if name == default_backend:
            current_idx = i
            break

    selected_idx = interactive_menu("Backend Selection", choices, default_idx=current_idx)
    if selected_idx >= 0:
        return choices[selected_idx][0]
    return default_backend


def select_startup_model(host: str, title: str = "Select Model") -> Optional[str]:
    """Let the user pick an installed model or download the default one.

    Returns the chosen model tag (which may still need downloading), or None if cancelled.
    When no models are installed, the only option is to download the default model.
    """
    installed = list_installed_ollama_models(host)
    options = [(name, "installed", True) for name in installed]
    offer_download = ENCHAN_DEFAULT_DOWNLOAD_MODEL not in installed
    if offer_download:
        options.append(
            (
                f"Download {ENCHAN_DEFAULT_DOWNLOAD_MODEL} ({ENCHAN_DEFAULT_DOWNLOAD_SIZE})",
                "from registry.ollama.ai",
                True,
            )
        )
    selected_idx = interactive_menu(title, options, default_idx=0)
    if selected_idx < 0:
        return None
    if offer_download and selected_idx == len(options) - 1:
        return ENCHAN_DEFAULT_DOWNLOAD_MODEL
    return installed[selected_idx]
