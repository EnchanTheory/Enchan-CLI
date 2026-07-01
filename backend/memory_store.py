from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
CLI_DIR = BACKEND_DIR.parent
MEMORY_DIR = CLI_DIR / "memory"

GUIDELINES_DIR = MEMORY_DIR / "guidelines"
KNOWLEDGE_DIR = MEMORY_DIR / "knowledge"

MEMORY_DIRS = (GUIDELINES_DIR, KNOWLEDGE_DIR)
MEMORY_SOURCES = (
    ("guidelines", GUIDELINES_DIR),
    ("knowledge", KNOWLEDGE_DIR),
)


def ensure_memory_dirs() -> None:
    for directory in MEMORY_DIRS:
        directory.mkdir(parents=True, exist_ok=True)

    legacy_decisions = MEMORY_DIR / "decisions"
    if legacy_decisions.exists() and legacy_decisions.is_dir():
        for path in legacy_decisions.glob("*.md"):
            try:
                path.rename(GUIDELINES_DIR / path.name)
            except OSError:
                pass


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _iter_markdown_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    files = [path for path in directory.rglob("*.md") if path.is_file()]
    return sorted(files, key=lambda path: (str(path.parent.relative_to(directory)), path.name.lower()))


def load_memory_context(max_chars: int = 24000) -> str:
    ensure_memory_dirs()

    sections: list[str] = []
    for source_name, source_dir in MEMORY_SOURCES:
        content_parts: list[str] = []
        for path in _iter_markdown_files(source_dir):
            text = _read_text(path)
            if not text:
                continue
            rel = path.relative_to(MEMORY_DIR)
            content_parts.append(f"<!-- Source: {rel} -->\n{text}")
        if content_parts:
            sections.append(f"<{source_name}>\n" + "\n\n".join(content_parts) + f"\n</{source_name}>")

    if not sections:
        return ""

    combined = "\n\n".join(sections)
    if len(combined) > max_chars:
        return combined[:max_chars].rstrip() + "\n...[Memory Truncated]..."
    return combined


def build_memory_prompt_section(memory_context: str) -> str:
    if not memory_context.strip():
        return ""
    return (
        "\n\n[Local Memory]\n"
        "You have access to curated local Markdown memory organized into XML blocks:\n"
        "- <guidelines>: durable operating rules and user/project preferences.\n"
        "- <knowledge>: curated local facts and reusable procedures.\n"
        "Treat these files as guidance, verify runtime behavior when it matters, and do not invent facts beyond them.\n\n"
        f"{memory_context.strip()}"
    )
