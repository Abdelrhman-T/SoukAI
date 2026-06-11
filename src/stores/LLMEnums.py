from enum import Enum


class LLMEnums(Enum):
    GROQ = "GROQ"
    OPENROUTER = "OPENROUTER"


class qroqEnums(Enum):
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"


class openrouterEnums(Enum):
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"