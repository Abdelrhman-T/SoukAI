from helpers.config import Settings

from .LLMEnums import LLMEnums
from .providers import groqProvider, openrouterProvider


class LLMProviderFactory:
    def __init__(self, config: Settings):
        self.config = config

    def create(self, provider_name: str):
        if provider_name == LLMEnums.GROQ.value:
            provider =  groqProvider(
                api_key=self.config.GROQ_API_KEY,
                default_input_max_characters=self.config.DEFAULT_INPUT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.DEFAULT_MAX_OUTPUT_TOKENS,
                default_generation_temperature=self.config.DEFAULT_TEMPERATURE,
            )
            provider.set_generation_model(self.config.GROQ_MODEL)
            return provider
        if provider_name == LLMEnums.OPENROUTER.value:
            provider = openrouterProvider(
                api_key=self.config.OPENROUTER_API_KEY,
                default_input_max_characters=self.config.DEFAULT_INPUT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.DEFAULT_MAX_OUTPUT_TOKENS,
                default_generation_temperature=self.config.DEFAULT_TEMPERATURE,
                api_url=self.config.OPENROUTER_URL,
            )
            provider.set_generation_model(self.config.OPENROUTER_MODEL)
            return provider
        return None
