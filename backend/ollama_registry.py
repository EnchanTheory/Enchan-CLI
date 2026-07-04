import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

ENCHAN_DEFAULT_DOWNLOAD_MODEL = "gemma4:e2b-it-qat"
ENCHAN_DEFAULT_DOWNLOAD_SIZE = "~4.3 GB"

def format_size(num_bytes: float) -> str:
    """Human-readable byte size, e.g. 4.3 GB."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def standalone_ollama_pull(model_name: str) -> bool:
    """
    Downloads an Ollama model directly from the registry without needing the Ollama daemon.
    Saves blobs and manifests exactly where Ollama expects them (~/.ollama/models/).
    """
    print(f"\n[System] Standalone registry pull initiated for: {model_name}")
    
    # Parse model name (e.g. gemma:2b or library/gemma:2b)
    if ":" not in model_name:
        model_name += ":latest"
    repo, tag = model_name.split(":", 1)
    if "/" not in repo:
        repo = f"library/{repo}"

    registry_base = "https://registry.ollama.ai/v2"
    manifest_url = f"{registry_base}/{repo}/manifests/{tag}"

    ollama_dir = Path.home() / ".ollama" / "models"
    blobs_dir = ollama_dir / "blobs"
    manifest_dir = ollama_dir / "manifests" / "registry.ollama.ai" / repo
    
    blobs_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    print(f"[System] Fetching manifest from registry.ollama.ai...")
    req = urllib.request.Request(manifest_url, headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            manifest_bytes = resp.read()
            manifest = json.loads(manifest_bytes)
    except urllib.error.HTTPError as e:
        print(f"[Error] Failed to fetch manifest ({e.code}). Model might not exist.")
        return False
    except Exception as e:
        print(f"[Error] Network error while fetching manifest: {e}")
        return False

    layers = manifest.get("layers", [])
    if "config" in manifest:
        layers.append(manifest["config"])

    total_size = sum(layer.get("size", 0) for layer in layers)
    downloaded_size = 0

    print(f"[System] Downloading {len(layers)} layers (Total: {format_size(total_size)})...")

    for layer in layers:
        digest = layer.get("digest")
        if not digest:
            continue
        
        blob_path = blobs_dir / digest.replace(":", "-")
        layer_size = layer.get("size", 0)

        if blob_path.exists() and blob_path.stat().st_size == layer_size:
            downloaded_size += layer_size
            continue

        blob_url = f"{registry_base}/{repo}/blobs/{digest}"
        
        try:
            req = urllib.request.Request(blob_url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                with open(blob_path, "wb") as f:
                    while True:
                        chunk = resp.read(8192 * 4)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Progress bar
                        if total_size > 0:
                            percent = int(downloaded_size * 100 / total_size)
                            percent = min(100, percent)
                            bar_length = 30
                            filled_length = int(bar_length * percent // 100)
                            bar = '█' * filled_length + '░' * (bar_length - filled_length)
                            sys.stdout.write(f"\r[Downloading] {bar} {percent}% ({format_size(downloaded_size)} / {format_size(total_size)}) ")
                            sys.stdout.flush()
        except Exception as e:
            print(f"\n[Error] Failed to download blob {digest[:15]}: {e}")
            if blob_path.exists():
                blob_path.unlink()  # Clean up partial
            return False

    # Finally, write the manifest
    manifest_file = manifest_dir / tag
    with open(manifest_file, "wb") as f:
        f.write(manifest_bytes)

    print("\n[System] Download complete! Model integrated into Ollama storage.\n")
    return True


def list_installed_ollama_models(host: str) -> list:
    """Return installed Ollama model tags via the API, falling back to local manifests."""
    try:
        url = host.rstrip("/") + "/api/tags"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        models = []
        try:
            manifest_root = Path.home() / ".ollama" / "models" / "manifests" / "registry.ollama.ai" / "library"
            if manifest_root.exists():
                for model_dir in manifest_root.iterdir():
                    if model_dir.is_dir():
                        for tag_file in model_dir.iterdir():
                            if tag_file.is_file():
                                models.append(f"{model_dir.name}:{tag_file.name}")
        except Exception:
            pass
        return models
