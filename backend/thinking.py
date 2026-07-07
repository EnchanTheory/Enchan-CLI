import re

THOUGHT_BLOCK_RE = re.compile(r"<(thought|think)>\s*(.*?)\s*</\1>", flags=re.DOTALL | re.IGNORECASE)


def split_thought_blocks(text: str) -> tuple[str, str]:
    """Return clean visible content and extracted fallback thinking text."""
    if not text:
        return text, ""
    thoughts: list[str] = []

    def _replace(match: re.Match) -> str:
        body = match.group(2).strip()
        if body:
            thoughts.append(body)
        return ""

    clean = THOUGHT_BLOCK_RE.sub(_replace, text).strip()
    return clean, "\n\n".join(thoughts).strip()


def strip_thought_blocks(text: str) -> str:
    """Remove <thought>/<think> fallback blocks from visible model content."""
    clean, _ = split_thought_blocks(text)
    return clean
