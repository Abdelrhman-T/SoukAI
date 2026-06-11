from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILES = (
    ROOT_DIR / ".env",
    ROOT_DIR / "src" / ".env",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=tuple(str(path) for path in ENV_FILES),
        extra="ignore",
    )
        
    APP_NAME: str
    APP_VERSION: str

    PRIMARY_LANG: str = "ar"
    DEFAULT_LANG: str = "en"

    BACKEND_LITERAL: List[str]
    GENERATION_BACKEND: str

    OPENROUTER_API_KEY: str
    OPENROUTER_URL: str

    OPENROUTER_MODEL_LITERAL: List[str]
    OPENROUTER_MODEL: str

    GROQ_API_KEY: str

    GROQ_MODEL: str


    DEFAULT_INPUT_MAX_CHARACTERS: int
    DEFAULT_MAX_OUTPUT_TOKENS: int
    DEFAULT_TEMPERATURE: float



    SAFETY_BLOCK_MESSAGE: str
    INJECTION_BLOCK_MESSAGE: str
    EMPTY_INPUT_MESSAGE: str
    LONG_INPUT_MESSAGE: str

    MISSING_ORDER_ID_MESSAGE:str 
    ORDER_NOT_FOUND_MESSAGE:str 



    GROQ_INPUT_PER_1K: float
    GROQ_OUTPUT_PER_1K: float

    OPENROUTER_INPUT_PER_1K: float
    OPENROUTER_OUTPUT_PER_1K: float

def getSettings():
    return Settings()
