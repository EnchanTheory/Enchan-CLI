import ctypes
import json
import platform
import sys
from pathlib import Path
from typing import Optional


BACKEND_DIR = Path(__file__).resolve().parent
MODE_STORY_ORDER = 1
ENCHAN_OK = 0
ENCHAN_ERROR_BUFFER_TOO_SMALL = -2
ENGINE_CLIENT_CONFIG = json.dumps(
    {"client": "EnchanTheory/Enchan-CLI", "protocol": 1},
    separators=(",", ":"),
).encode("utf-8")


def get_engine_lib_path() -> Path:
    base_dir = BACKEND_DIR / "bin"
    if sys.platform == "win32":
        return base_dir / "win-x64" / "enchan.dll"
    if sys.platform == "darwin":
        arch = "arm64" if platform.machine() == "arm64" else "x64"
        return base_dir / f"macos-{arch}" / "libenchan.dylib"
    return base_dir / "linux-x64" / "libenchan.so"


ENGINE_LIB_PATH = get_engine_lib_path()
COSMIC_AVAILABLE = ENGINE_LIB_PATH.exists()
_ENGINE_DLL: Optional[ctypes.CDLL] = None
_PRELOADED_ENGINE_DEPS: list[ctypes.CDLL] = []


def _preload_engine_deps(base_dir: Path) -> None:
    """Preload sibling ggml libraries so libenchan can resolve dynamic symbols."""
    if sys.platform == "win32":
        return
    mode = getattr(ctypes, "RTLD_GLOBAL", 0)
    ext = ".dylib" if sys.platform == "darwin" else ".so"
    order = ("libggml-base", "libggml-cpu", "libggml-blas", "libggml-metal", "libggml")
    for name in order:
        candidates = sorted(base_dir.glob(f"{name}.*{ext}")) or list(base_dir.glob(f"{name}{ext}"))
        for candidate in candidates:
            try:
                _PRELOADED_ENGINE_DEPS.append(ctypes.CDLL(str(candidate), mode=mode))
                break
            except OSError:
                continue


def get_engine_dll() -> ctypes.CDLL:
    global _ENGINE_DLL
    if _ENGINE_DLL is not None:
        return _ENGINE_DLL
    if not ENGINE_LIB_PATH.exists():
        raise RuntimeError(f"Enchan Engine library not found: {ENGINE_LIB_PATH}")

    _preload_engine_deps(ENGINE_LIB_PATH.parent)
    dll = ctypes.CDLL(str(ENGINE_LIB_PATH))
    dll.enchan_engine_init.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    dll.enchan_engine_init.restype = ctypes.c_int
    dll.enchan_engine_has_capability.argtypes = [ctypes.c_char_p]
    dll.enchan_engine_has_capability.restype = ctypes.c_int
    dll.enchan_compression_select_utf8.argtypes = [
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_char_p),
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_int,
    ]
    dll.enchan_compression_select_utf8.restype = ctypes.c_int

    status = dll.enchan_engine_init(b"enchan-cli", ENGINE_CLIENT_CONFIG)
    if status != ENCHAN_OK:
        raise RuntimeError(f"Enchan Engine init failed: {status}")
    if not dll.enchan_engine_has_capability(b"compression.enchan"):
        raise RuntimeError("Enchan Engine capability is unavailable: compression.enchan")

    _ENGINE_DLL = dll
    return dll


def initialize_engine_session() -> bool:
    """Initialize the Enchan CLI client protocol and report RAG capability."""
    dll = get_engine_dll()
    return bool(dll.enchan_engine_has_capability(b"rag.enchan"))

def select_text_indices(
    query: str,
    candidates: list[str],
    budget: int,
    *,
    preserve_order: bool = False,
) -> list[int]:
    if budget <= 0 or not candidates:
        return []

    dll = get_engine_dll()
    encoded_candidates = [candidate.encode("utf-8", errors="replace") for candidate in candidates]
    candidate_ptrs = (ctypes.c_char_p * len(encoded_candidates))(*encoded_candidates)
    candidate_lengths = (ctypes.c_int * len(encoded_candidates))(*(len(candidate) for candidate in encoded_candidates))
    out_capacity = min(len(encoded_candidates), budget)
    out_indices = (ctypes.c_int * out_capacity)()
    mode_flags = MODE_STORY_ORDER if preserve_order else 0

    count = dll.enchan_compression_select_utf8(
        query.encode("utf-8", errors="replace"),
        candidate_ptrs,
        candidate_lengths,
        len(encoded_candidates),
        budget,
        mode_flags,
        out_indices,
        out_capacity,
    )
    if count == ENCHAN_ERROR_BUFFER_TOO_SMALL:
        raise RuntimeError("Enchan Engine selection output buffer was too small")
    if count <= 0:
        raise RuntimeError(f"Enchan Engine selection failed: {count}")

    selected = []
    seen = set()
    for i in range(min(count, out_capacity)):
        idx = int(out_indices[i])
        if 0 <= idx < len(candidates) and idx not in seen:
            selected.append(idx)
            seen.add(idx)
    if not selected:
        raise RuntimeError("Enchan Engine selection returned no valid indices")
    if preserve_order:
        selected.sort()
    return selected[:budget]
