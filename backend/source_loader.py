import os
import re
from pathlib import Path


def is_binary_file(file_path: Path) -> bool:
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            return b"\x00" in chunk
    except Exception:
        return True


def read_directory_recursive(dir_path: Path, max_chars: int = 150000):
    ignore_folders = {
        ".git",
        ".venv",
        ".venv_cuda",
        "__pycache__",
        "node_modules",
        "benchmarks",
        ".antigravitycli",
        "Cover-art",
        "shiba",
    }
    ignore_extensions = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".webp", ".zip", ".exe", ".dll", ".pyc"}

    combined_text = []
    loaded_files = []
    total_chars = 0

    for root, dirs, files in os.walk(dir_path):
        dirs[:] = [d for d in dirs if d not in ignore_folders]

        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() in ignore_extensions:
                continue
            if is_binary_file(file_path):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if content.strip():
                    rel_path = file_path.relative_to(dir_path)
                    header = f"\n--- File: {rel_path} ---\n"
                    combined_text.append(header + content + "\n")
                    loaded_files.append(str(rel_path))
                    total_chars += len(content)
                    if total_chars >= max_chars:
                        combined_text.append(f"\n[Truncated: Exceeded max character limit of {max_chars}]\n")
                        break
            except Exception:
                pass
        if total_chars >= max_chars:
            break

    return "".join(combined_text), loaded_files


def extract_path_and_query(user_input: str):
    text = user_input.strip()

    quoted_match = re.search(r'"([a-zA-Z]:[\\/][^"]+)"|\'([a-zA-Z]:[\\/][^\']+)\'', text)
    if quoted_match:
        raw_path = quoted_match.group(1) or quoted_match.group(2)
        p = Path(raw_path)
        if p.exists():
            before = text[: quoted_match.start()].strip()
            after = text[quoted_match.end() :].strip()
            query = " ".join(part for part in (before, after) if part)
            return p, query

    drive_match = re.search(r"[a-zA-Z]:[\\/]", text)
    if drive_match:
        start = drive_match.start()
        tail = text[start:]
        for end in range(len(tail), 2, -1):
            raw_path = tail[:end].rstrip()
            if not raw_path:
                continue
            p = Path(raw_path)
            if p.exists():
                before = text[:start].strip()
                after = tail[end:].strip()
                query = " ".join(part for part in (before, after) if part)
                return p, query

    p_fallback = Path(text.strip("\"'"))
    if p_fallback.exists():
        return p_fallback, ""

    return None, user_input


import base64

def find_and_encode_images(text: str) -> list[str]:
    """Scans the text for paths to existing image files, handling spaces, and returns their Base64 representations."""
    import re
    image_paths = []
    
    # 1. Match quoted image paths
    quoted_pattern = r'["\']([^"\']+\.(?:png|jpg|jpeg|gif|webp))["\']'
    for m in re.findall(quoted_pattern, text, re.IGNORECASE):
        p = Path(m.strip())
        if p.exists() and p.is_file():
            image_paths.append(p)
            
    # 2. Match unquoted image paths (handles spaces by joining split words)
    words = text.split()
    for i in range(len(words)):
        for j in range(i + 1, len(words) + 1):
            candidate = " ".join(words[i:j]).strip(".,;:?!()[]{}")
            if candidate.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                p = Path(candidate)
                if p.exists() and p.is_file() and p not in image_paths:
                    image_paths.append(p)
            
    encoded_images = []
    for p in image_paths:
        try:
            with open(p, "rb") as f:
                encoded_images.append(base64.b64encode(f.read()).decode("utf-8"))
        except Exception:
            pass
    return encoded_images
