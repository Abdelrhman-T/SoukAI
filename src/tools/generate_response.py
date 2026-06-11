import json
import logging
import re
from collections.abc import Mapping

from pydantic import BaseModel, field_validator

from helpers.config import Settings
from stores.LLMProviderFactory import LLMProviderFactory

logger = logging.getLogger(__name__)
JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _normalize_provider_response(answer):
    if isinstance(answer, Mapping):
        text = str(answer.get("text", "")).strip()
        usage = answer.get("usage", {})
        if not isinstance(usage, Mapping):
            usage = {}
        return {
            "text": text,
            "input_tokens": int(usage.get("input_tokens", 0) or 0),
            "output_tokens": int(usage.get("output_tokens", 0) or 0),
        }

    return {
        "text": str(answer or "").strip(),
        "input_tokens": 0,
        "output_tokens": 0,
    }


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

    normalized_answer = _normalize_provider_response(answer)

    if not normalized_answer["text"]:
        raise EmptyResponseError(
            f"{provider_name} returned an empty response."
        )

    return {
        "provider": provider_name,
        "answer": normalized_answer["text"],
        "input_tokens": normalized_answer["input_tokens"],
        "output_tokens": normalized_answer["output_tokens"],
    }


def _parse_draft_payload(answer: str) -> dict[str, str | None]:
    if not answer or not answer.strip():
        raise EmptyResponseError("Draft response payload was empty.")

    match = JSON_BLOCK_RE.search(answer.strip())
    payload_text = match.group(0) if match else answer.strip()

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        try:
            payload = json.loads(payload_text.replace("'", '"'))
        except json.JSONDecodeError as exc:
            raise ResponseGenerationError(
                "Draft response payload was not valid JSON."
            ) from exc

    if not isinstance(payload, dict):
        raise ResponseGenerationError("Draft response payload must be a JSON object.")

    response_text = str(payload.get("response", "")).strip()
    if not response_text:
        raise EmptyResponseError("Draft response did not include `response`.")

    priority = payload.get("priority")
    reason = payload.get("reason")

    return {
        "response": response_text,
        "priority": str(priority).strip() if priority is not None else "",
        "reason": str(reason).strip() if reason is not None else "",
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

    raw_response = llm_response(
        provider_name=provider_name,
        prompt=Prompt(
            sys_prompt=sys_prompt,
            user_prompt="\n".join(prompt_sections),
        ),
        app_settings=app_settings,
    )

    parsed_payload = _parse_draft_payload(raw_response["answer"])

    return {
        "provider": raw_response["provider"],
        "answer": parsed_payload["response"],
        "response": parsed_payload["response"],
        "priority": parsed_payload["priority"],
        "reason": parsed_payload["reason"],
        "input_tokens": raw_response.get("input_tokens", 0),
        "output_tokens": raw_response.get("output_tokens", 0),
    }
