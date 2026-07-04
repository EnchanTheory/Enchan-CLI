import re

def strip_thought_blocks(text: str) -> str:
    """Removes <thought>...</thought> and <think>...</think> blocks to keep multi-turn context clean."""
    if not text:
        return text
    text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()
