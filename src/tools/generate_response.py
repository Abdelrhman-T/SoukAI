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


def draft_response(
    intent: str,
    context: str,
    *,
    provider_name: str,
    app_settings: Settings,
    sys_prompt: str = "",
):
    if not context or not context.strip():
        raise PromptValidationError("`context` must not be empty.")

    prompt_sections = []

    if intent and intent.strip():
        prompt_sections.append(f"النية المصنفة: {intent.strip()}")

    prompt_sections.append(f"السياق:\n{context.strip()}")
    prompt_sections.append("اكتب ردا عربيا قصيرا ومفيدا للعميل.")

    return llm_response(
        provider_name=provider_name,
        prompt=Prompt(
            sys_prompt=sys_prompt,
            user_prompt="\n".join(prompt_sections),
        ),
        app_settings=app_settings,
    )
