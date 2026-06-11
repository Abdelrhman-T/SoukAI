def is_empty(text: str) -> bool:
    return not text or not text.strip()


def is_long(text: str, max_chars: int = 1200) -> bool:
    return len(text or "") > max_chars
