from .LLMEnums import LLMEnums
from .providers import groqProvider, openrouterProvider


class LLMProviderFactory:
    def __init__(self, config: dict):
        self.config = config

    def create(self, provider_name: str):
        if provider_name == LLMEnums.GROQ.value:
            return groqProvider(
                api_key=self.config.GROQ_API_KEY,
                default_input_max_characters=self.config.DEFAULT_INPUT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.DEFAULT_MAX_OUTPUT_TOKENS,
                default_generation_temperature=self.config.DEFAULT_TEMPERATURE,
            )
        if provider_name == LLMEnums.OPENROUTER.value:
            return openrouterProvider(
                api_key=self.config.OPENROUTER_API_KEY,
                default_input_max_characters=self.config.DEFAULT_INPUT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.DEFAULT_MAX_OUTPUT_TOKENS,
                default_generation_temperature=self.config.DEFAULT_TEMPERATURE,
                model=self.config.OPENROUTER_MODEL,
                url=self.config.OPENROUTER_URL,
            )
        return None
