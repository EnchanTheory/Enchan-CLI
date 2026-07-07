VALID_KV_CACHE_TYPES = {"q4_0", "q8_0", "f16"}
DEFAULT_KV_CACHE_TYPE = "q4_0"


def normalize_kv_cache_type(value: str | None) -> str:
    text = str(value or DEFAULT_KV_CACHE_TYPE).strip().lower()
    if text not in VALID_KV_CACHE_TYPES:
        return DEFAULT_KV_CACHE_TYPE
    return text


def apply_enchan_kv_cache_patch(kv_cache_type: str | None) -> str:
    """Inject llama.cpp KV-cache quantization flags into Enchan llama-server startup.

    This keeps the large backend launcher stable while ensuring every subsequent
    llama-server spawn receives --cache-type-k/v unless the command already set them.
    """
    kv_type = normalize_kv_cache_type(kv_cache_type)

    import backend.enchan_llama_backend as llama_backend

    original = getattr(llama_backend, "_ENCHAN_ORIGINAL_SPAWN_SERVER_PROCESS", None)
    if original is None:
        original = llama_backend._spawn_server_process
        llama_backend._ENCHAN_ORIGINAL_SPAWN_SERVER_PROCESS = original

    def _spawn_server_process_with_kv_cache(cmd, env, creationflags):
        patched_cmd = list(cmd)
        if "--cache-type-k" not in patched_cmd and "-ctk" not in patched_cmd:
            patched_cmd.extend(["--cache-type-k", kv_type])
        if "--cache-type-v" not in patched_cmd and "-ctv" not in patched_cmd:
            patched_cmd.extend(["--cache-type-v", kv_type])
        return original(patched_cmd, env, creationflags)

    llama_backend._spawn_server_process = _spawn_server_process_with_kv_cache
    return kv_type
