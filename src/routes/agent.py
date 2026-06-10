from functools import lru_cache
from typing import Any, Optional, TypedDict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from helpers.config import Settings, getSettings
from prompts.system_prompt import sys_prompt
from stores.LLMEnums import LLMEnums
from tools.arabic_utils import detect_script, normalize_arabic
from tools.generate_response import (EmptyResponseError, Prompt,
                                     ProviderInitializationError,
                                     ResponseGenerationError, llm_response)
from tools.safety import detect_prompt_injection, profanity_filter
from tools.validation import is_empty, is_long

agent_router = APIRouter(prefix="/api/v1/agent", tags=["api_v1", "agent"])


class AgentRequest(BaseModel):
    text: str


class AgentState(TypedDict, total=False):
    text: str
    normalized_text: str
    script: str
    is_safe: bool
    injection_detected: bool
    blocked_reason: Optional[str]
    provider: str
    model: str
    answer: str
    max_input_characters: int
    app_settings: Settings


def _preprocess_message(state: AgentState) -> AgentState:
    normalized_text = normalize_arabic(state["text"]) 
    return {
        "normalized_text": normalized_text,
        "script": detect_script(normalized_text),
    }


def _safety_check(state: AgentState) -> AgentState:
    normalized_text = state["normalized_text"]

    if is_empty(normalized_text):
        return {
            "is_safe": False,
            "injection_detected": False,
            "blocked_reason": state["app_settings"].EMPTY_INPUT_MESSAGE,
        }

    if is_long(normalized_text, state["max_input_characters"]):
        return {
            "is_safe": False,
            "injection_detected": False,
            "blocked_reason": state["app_settings"].LONG_INPUT_MESSAGE,
        }

    if profanity_filter(normalized_text):
        return {
            "is_safe": False,
            "injection_detected": False,
            "blocked_reason": state["app_settings"].SAFETY_BLOCK_MESSAGE,
        }

    injection_detected = detect_prompt_injection(normalized_text)
    if injection_detected:
        return {
            "is_safe": False,
            "injection_detected": True,
            "blocked_reason": state["app_settings"].INJECTION_BLOCK_MESSAGE,
        }

    return {
        "is_safe": True,
        "injection_detected": False,
        "blocked_reason": None,
    }


def _answer(state: AgentState) -> AgentState:
    provider_name = state["provider"]
    model_name = state["model"]

    if not state.get("is_safe", False):
        return {
            "provider": provider_name,
            "model": model_name,
            "answer": state["blocked_reason"],
        }

    response = llm_response(
        provider_name=provider_name,
        prompt=Prompt(sys_prompt=sys_prompt, user_prompt=state["normalized_text"]),
        app_settings=state["app_settings"],
    )

    return {
        "provider": response["provider"],
        "model": model_name,
        "answer": response["answer"],
    }


@lru_cache(maxsize=1)
def _graph_factory() -> Any:
    workflow = StateGraph(AgentState)
    workflow.add_node(
        "preprocess_node", RunnableLambda(_preprocess_message)
    )
    workflow.add_node(
        "safety_check_node", RunnableLambda(_safety_check),
    )
    workflow.add_node("answer_node", RunnableLambda(_answer))

    workflow.add_edge(START, "preprocess_node")
    workflow.add_edge("preprocess_node", "safety_check_node")
    workflow.add_edge("safety_check_node", "answer_node")
    workflow.add_edge("answer_node", END)

    return workflow.compile()


@agent_router.post("/answer")
async def answer_with_agent(
    request: AgentRequest,
    app_settings: Settings = Depends(getSettings),
):
    graph = _graph_factory()

    try:
        result = graph.invoke(
            {
                "text": request.text,
                "provider": LLMEnums.GROQ.value,
                "model": app_settings.GROQ_MODEL,
                "max_input_characters": app_settings.DEFAULT_INPUT_MAX_CHARACTERS,
                "app_settings": app_settings,
            }
        )
    except ProviderInitializationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except (ResponseGenerationError, EmptyResponseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    if result.get("blocked_reason") == app_settings.EMPTY_INPUT_MESSAGE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=app_settings.EMPTY_INPUT_MESSAGE,
        )

    if result.get("blocked_reason") == app_settings.LONG_INPUT_MESSAGE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=app_settings.LONG_INPUT_MESSAGE,
        )

    return JSONResponse(
        content={
            "provider": result.get("provider", LLMEnums.GROQ.value),
            "model": result.get("model", app_settings.GROQ_MODEL),
            "text": result.get("normalized_text", normalize_arabic(request.text)),
            "script": result.get("script", detect_script(request.text)),
            "is_safe": result.get("is_safe", False),
            "injection_detected": result.get("injection_detected", False),
            "answer": result["answer"],
        }
    )
