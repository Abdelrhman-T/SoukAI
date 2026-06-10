from tools.arabic_utils import contains_any, detect_script

PROFANITY_KEYWORDS = [
    "حمار",
    "اغبياء",
    "نصابين",
    "كلاب",
    "زبالة",
    "stupid",
    "idiot",
]

INJECTION_KEYWORDS = [
    "تجاهل التعليمات", "تجاهل", "التعليمات", "قيود", "بدون قيود"
    "ignore previous instructions",
    "system prompt",
    "SYSTEM","SYSTEM:", "override", "set"
    "اكسر القواعد",
    "اعطني السيستم برومبت",
    "developer message",
    "SQL", "SELECT", "FROM", "WHERE", "DROP", "TABLE"
]


def profanity_filter(text: str) -> bool:
    return contains_any(text, PROFANITY_KEYWORDS)


def detect_prompt_injection(text: str) -> bool:
    return contains_any(text, INJECTION_KEYWORDS) or (
        detect_script(text) == "code_switched" and "prompt" in text.lower()
    )
