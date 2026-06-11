import re
from typing import List

ARABIC_DIACRITICS = re.compile(r"[\u0617-\u061A\u064B-\u0652]")
TATWEEL = "\u0640"
PUNCT_RE = re.compile(r"[^\w\s\u0600-\u06FF]")
WHITESPACE_RE = re.compile(r"\s+")


def normalize_arabic(text: str) -> str:
    normalized = text or ""
    normalized = ARABIC_DIACRITICS.sub("", normalized)
    normalized = normalized.replace(TATWEEL, "")
    normalized = normalized.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    normalized = normalized.replace("ة", "ه").replace("ى", "ي")
    normalized = WHITESPACE_RE.sub(" ", normalized).strip()
    normalized = re.sub(r'(.)\1{2,}', r'\1', normalized)
    return normalized


def strip_punctuation(text: str) -> str:
    return PUNCT_RE.sub(" ", text)


def tokenize(text: str) -> List[str]:
    clean = strip_punctuation(normalize_arabic(text.lower()))
    return [token for token in clean.split() if token]


def contains_any(text: str, keywords: List[str]) -> bool:
    haystack = normalize_arabic(text.lower())
    return any(normalize_arabic(keyword.lower()) in haystack for keyword in keywords)


def ratio_hits(tokens: List[str], keywords: List[str]) -> float:
    if not keywords:
        return 0.0
    matched = sum(1 for keyword in keywords if normalize_arabic(keyword) in tokens)
    return matched / len(keywords)


def detect_script(text: str) -> str:
    arabic_count = sum(1 for char in text if "\u0600" <= char <= "\u06FF")
    latin_count = sum(1 for char in text if ("a" <= char.lower() <= "z"))
    if arabic_count and latin_count:
        return "code_switched"
    if arabic_count:
        return "arabic"
    if latin_count:
        return "latin"
    return "unknown"
