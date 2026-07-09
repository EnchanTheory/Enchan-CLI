import re
import unicodedata


_EMOJI_RE = re.compile(
    r'[\U0001F600-\U0001F64F]'
    r'|[\U0001F300-\U0001F5FF]'
    r'|[\U0001F680-\U0001F6FF]'
    r'|[\U0001F700-\U0001F77F]'
    r'|[\U0001F780-\U0001F7FF]'
    r'|[\U0001F800-\U0001F8FF]'
    r'|[\U0001F900-\U0001F9FF]'
    r'|[\U0001FA00-\U0001FA6F]'
    r'|[\U0001FA70-\U0001FAFF]'
    r'|[\u2600-\u26FF]'
    r'|[\u2700-\u27BF]'
    r'|[\uFE0F]'
)


def strip_emojis(text: str) -> str:
    return _EMOJI_RE.sub('', text)


def visual_len(text: str) -> int:
    width = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in "WF" else 1
    return width


def truncate_visual(text: str, max_width: int) -> str:
    if max_width <= 0:
        return ""
    if visual_len(text) <= max_width:
        return text
    marker = "..."
    limit = max(0, max_width - len(marker))
    width = 0
    result = ""
    for char in text:
        char_width = 0 if unicodedata.combining(char) else (2 if unicodedata.east_asian_width(char) in "WF" else 1)
        if width + char_width > limit:
            break
        result += char
        width += char_width
    return result + marker
