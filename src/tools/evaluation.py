import json
import logging
import random
import re
import time
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from helpers.config import ROOT_DIR, Settings
from prompts.judge_prompt import llm_as_judge
from stores.LLMEnums import LLMEnums
from tools.evaluation_store import save_evaluation_to_supabase
from tools.generate_response import (Prompt, ProviderInitializationError,
                                     llm_response)

logger = logging.getLogger(__name__)
JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

FAILURE_CATEGORIES = [
    "none",
    "incorrect_answer",
    "not_actionable",
    "wrong_dialect",
    "bad_tone",
    "unsupported_promise",
    "missed_escalation",
    "generic_response",
]


class JudgeResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    correctness: int
    helpfulness: int
    dialect_match: int
    tone: int
    overall_score: float
    passed: bool
    failure_category: str
    short_reason: str

    @field_validator("correctness", "helpfulness", "dialect_match", "tone")
    @classmethod
    def validate_score(cls, value: int) -> int:
        if value < 1 or value > 5:
            raise ValueError("Judge scores must be between 1 and 5.")
        return value

    @field_validator("failure_category")
    @classmethod
    def validate_failure_category(cls, value: str) -> str:
        if value not in FAILURE_CATEGORIES:
            raise ValueError("Invalid failure category.")
        return value

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "JudgeResult":
        normalized_payload = dict(payload)

        if "pass" in normalized_payload and "passed" not in normalized_payload:
            normalized_payload["passed"] = normalized_payload.pop("pass")

        result = cls.model_validate(normalized_payload)

        if result.passed and result.failure_category != "none":
            raise ValueError("Passing evaluations must use failure_category='none'.")

        return result


def should_evaluate_response(sample_rate: float = 0.5) -> bool:
    if sample_rate < 0 or sample_rate > 1:
        raise ValueError("sample_rate must be between 0 and 1.")
    return random.random() < sample_rate


def _parse_judge_payload(answer: str) -> JudgeResult:
    if not answer or not answer.strip():
        raise ValueError("Judge returned an empty payload.")

    match = JSON_BLOCK_RE.search(answer.strip())
    payload_text = match.group(0) if match else answer.strip()

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        try:
            payload = json.loads(payload_text.replace("'", '"'))
        except json.JSONDecodeError as exc:
            raise ValueError("Judge payload was not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValueError("Judge payload must be a JSON object.")

    try:
        return JudgeResult.from_payload(payload)
    except (ValidationError, ValueError) as exc:
        raise ValueError("Judge payload failed validation.") from exc



def _render_judge_prompt(
    *,
    review: str,
    intent: str,
    routed_team: str,
    draft_response_ar: str,
) -> str:
    return (
        llm_as_judge.replace("{review}", review)
        .replace("{intent}", intent)
        .replace("{routed_team}", routed_team)
        .replace("{draft_response_ar}", draft_response_ar)
    )


def _resolve_judge_target(app_settings: Settings) -> tuple[str, str]:
    backend = app_settings.JUDGE_BACKEND.upper()

    if backend == LLMEnums.GROQ.value:
        return LLMEnums.GROQ.value, app_settings.MODEL_JUDGE

    if backend == LLMEnums.OPENROUTER.value:
        return LLMEnums.OPENROUTER.value, app_settings.MODEL_JUDGE

    raise ProviderInitializationError(
        f"Unsupported judge backend: {app_settings.JUDGE_BACKEND}"
    )


def evaluate_response(
    *,
    review: str,
    intent: str,
    routed_team: str,
    draft_response_ar: str,
    app_settings: Settings,
    sample_rate: float = 0.5,
) -> dict[str, Any]:
    evaluated_at = datetime.now().astimezone().isoformat(timespec="seconds")

    if not should_evaluate_response(sample_rate=sample_rate):
        return {
            "sampled_for_evaluation": False,
            "evaluation_status": "skipped",
            "evaluation_time_ms": 0.0,
        }

    provider_name, model_name = _resolve_judge_target(app_settings)

    base_row = {
        "evaluated_at": evaluated_at,
        "evaluation_provider": provider_name,
        "evaluation_model": model_name,
        "customer_message": review,
        "predicted_intent": intent,
        "routed_team": routed_team,
        "generated_response": draft_response_ar,
    }

    started_at = time.perf_counter()
    prompt_text = _render_judge_prompt(
        review=review,
        intent=intent,
        routed_team=routed_team,
        draft_response_ar=draft_response_ar,
    )

    try:
        judge_response = llm_response(
            provider_name=provider_name,
            prompt=Prompt(user_prompt=prompt_text),
            app_settings=app_settings,
            model_name=model_name,
        )
        parsed_judgment = _parse_judge_payload(judge_response["answer"])
        evaluation_time_ms = round((time.perf_counter() - started_at) * 1000, 2)

        row = {
            **base_row,
            "evaluation_status": "judged",
            "evaluation_time_ms": evaluation_time_ms,
            "correctness": parsed_judgment.correctness,
            "helpfulness": parsed_judgment.helpfulness,
            "dialect_match": parsed_judgment.dialect_match,
            "tone": parsed_judgment.tone,
            "overall_score": parsed_judgment.overall_score,
            "pass": parsed_judgment.passed,
            "failure_category": parsed_judgment.failure_category,
            "short_reason": parsed_judgment.short_reason,
            "judge_input_tokens": judge_response.get("input_tokens", 0),
            "judge_output_tokens": judge_response.get("output_tokens", 0),
            "evaluation_error": "",
        }

        save_evaluation_to_supabase(row, app_settings)

        return {
            "sampled_for_evaluation": True,
            "evaluation_status": "judged",
            "evaluation_time_ms": evaluation_time_ms,
            "evaluation_pass": parsed_judgment.passed,
        }
    except Exception as exc:
        evaluation_time_ms = round((time.perf_counter() - started_at) * 1000, 2)

        logger.exception(
            "Response evaluation failed status=error provider=%s model=%s intent=%s routed_team=%s evaluation_time_ms=%s",
            provider_name,
            model_name,
            intent,
            routed_team,
            evaluation_time_ms,
        )

        row = {
            **base_row,
            "evaluation_status": "error",
            "evaluation_time_ms": evaluation_time_ms,
            "correctness": None,
            "helpfulness": None,
            "dialect_match": None,
            "tone": None,
            "overall_score": None,
            "pass": None,
            "failure_category": None,
            "short_reason": None,
            "judge_input_tokens": 0,
            "judge_output_tokens": 0,
            "evaluation_error": str(exc),
        }

        save_evaluation_to_supabase(row, app_settings)

        return {
            "sampled_for_evaluation": True,
            "evaluation_status": "error",
            "evaluation_time_ms": evaluation_time_ms,
            "evaluation_error": str(exc),
        }