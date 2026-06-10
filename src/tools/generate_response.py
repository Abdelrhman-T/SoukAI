import logging

from pydantic import BaseModel, field_validator

from helpers.config import Settings
from stores.LLMProviderFactory import LLMProviderFactory

logger = logging.getLogger(__name__)


class Prompt(BaseModel):
    sys_prompt: str = ""
    user_prompt: str

    @field_validator("user_prompt")
    @classmethod
    def validate_user_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("`user_prompt` must not be empty.")
        return value


class PromptValidationError(ValueError):
    pass


class ProviderInitializationError(RuntimeError):
    pass


class ResponseGenerationError(RuntimeError):
    pass


class EmptyResponseError(RuntimeError):
    pass


def llm_response(
    provider_name: str,
    prompt: Prompt,
    app_settings: Settings,
):
    provider_factory = LLMProviderFactory(app_settings)
    provider = provider_factory.create(provider_name)

    if provider is None:
        raise ProviderInitializationError(
            f"Failed to initialize provider: {provider_name}"
        )

    chat_history = []

    if prompt.sys_prompt.strip():
        system_role = provider.enum.SYSTEM.value
        chat_history.append(
            provider.construct_prompt(
                prompt=prompt.sys_prompt,
                role=system_role,
            )
        )

    try:
        answer = provider.generate_text(
            prompt=prompt.user_prompt,
            chat_history=chat_history,
            max_output_tokens=app_settings.DEFAULT_MAX_OUTPUT_TOKENS,
            temperature=app_settings.DEFAULT_TEMPERATURE,
        )
    except Exception as exc:
        logger.exception("%s generation failed", provider_name)
        raise ResponseGenerationError(
            f"{provider_name} request failed."
        ) from exc

    if not answer or not str(answer).strip():
        raise EmptyResponseError(
            f"{provider_name} returned an empty response."
        )

    return {
        "provider": provider_name,
        "answer": answer,
    }