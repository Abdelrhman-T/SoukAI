from functools import lru_cache
from typing import Any, Optional, TypedDict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from helpers import intent_rules
from helpers.config import Settings, getSettings
from prompts.system_prompt import draft_response_prompt
from stores.LLMEnums import LLMEnums
from tools.arabic_utils import detect_script, normalize_arabic
from tools.classification import classify_intent
from tools.generate_response import (EmptyResponseError,
                                     ProviderInitializationError,
                                     ResponseGenerationError, draft_response)
from tools.retrieval import extract_order_id, lookup_order, search_kb
from tools.safety import detect_prompt_injection, profanity_filter
from tools.validation import is_empty, is_long

agent_router = APIRouter(prefix="/api/v1/agent", tags=["api_v1", "agent"])

MISSING_ORDER_ID_MESSAGE = "من فضلك أرسل رقم الطلب أو رقم الحجز حتى أقدر أساعدك."
ORDER_NOT_FOUND_MESSAGE = "لم أتمكن من العثور على الطلب. تأكد من رقم الطلب وأعد إرساله."


class AgentRequest(BaseModel):
    text: str


class AgentState(TypedDict, total=False):
    text: str
    normalized_text: str
    script: str
    is_safe: bool
    injection_detected: bool
    blocked_reason: Optional[str]
    intent: str
    order_id: Optional[str]
    order: Optional[dict[str, Any]]
    kb_matches: list[dict[str, Any]]
    routed_team: str
    requires_human: bool
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


def _classify_intent(state: AgentState) -> AgentState:
    if not state.get("is_safe", False):
        return {"intent": intent_rules.DEFAULT_INTENT}

    return {
        "intent": classify_intent(
            state["normalized_text"],
        )
    }


def _extract_order_id(state: AgentState) -> AgentState:
    order_id = extract_order_id(state["normalized_text"])
    if not order_id:
        return {
            "order_id": None,
            "routed_team": "Auto Response",
            "requires_human": False,
        }
    return {
        "order_id": extract_order_id(state["normalized_text"]),
    }


def _lookup_order(state: AgentState) -> AgentState:
    order_id = state.get("order_id")
    if not state.get("is_safe", False) or not order_id:
        return {
            "order": None,
            "routed_team": "Auto Response",
            "requires_human": False,
        }

    return {
        "order": lookup_order(order_id),
    }


def _search_kb(state: AgentState) -> AgentState:
    if not state.get("is_safe", False):
        return {
            "kb_matches": [],
            "routed_team": "Auto Response",
            "requires_human": False,
        }

    kb_matches = search_kb(
        state["normalized_text"],
        state.get("intent", intent_rules.DEFAULT_INTENT),
    )
    default_route = "Auto Response"

    if kb_matches:
        default_route = kb_matches[0].get("default_route", default_route)

    if not state["order_id"]:
        return {
            "kb_matches": kb_matches,
            "routed_team": "Auto Response",
            "requires_human": False,
        }

    return {
        "kb_matches": kb_matches,
        "routed_team": default_route,
        "requires_human": default_route != "Auto Response",
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

    if not state.get("order_id") and not state.get("injection_detected", False):
        return {
            "provider": provider_name,
            "model": model_name,
            "answer": MISSING_ORDER_ID_MESSAGE,
        }

    if state.get("order_id") and not state.get("order"):
        return {
            "provider": provider_name,
            "model": model_name,
            "answer": ORDER_NOT_FOUND_MESSAGE,
        }

    context_parts = [f"رسالة العميل:\n{state['normalized_text']}"]

    if state.get("kb_matches"):
        kb_item = state["kb_matches"][0]
        context_parts.append(
            (
                "المعرفة المسترجعة:\n"
                f"التوجيه الافتراضي: {state.get('routed_team', 'Auto Response')}\n"
                f"مرجع السياسة: {kb_item.get('title_ar', '')}\n"
                f"محتوى السياسة: {kb_item.get('content_ar', '')}"
            )
        )

    response = draft_response(
        intent=state.get("intent", intent_rules.DEFAULT_INTENT),
        context="\n\n".join(context_parts),
        provider_name=provider_name,
        app_settings=state["app_settings"],
        sys_prompt=draft_response_prompt,
    )

    return {
        "provider": response["provider"],
        "model": model_name,
        "answer": response["answer"],
    }


@lru_cache(maxsize=1)
def _graph_factory() -> Any:
    workflow = StateGraph(AgentState)
    workflow.add_node("preprocess_node", RunnableLambda(_preprocess_message))
    workflow.add_node("safety_check_node", RunnableLambda(_safety_check))
    workflow.add_node("classify_intent_node", RunnableLambda(_classify_intent))
    workflow.add_node("extract_order_id_node", RunnableLambda(_extract_order_id))
    workflow.add_node("lookup_order_node", RunnableLambda(_lookup_order))
    workflow.add_node("search_kb_node", RunnableLambda(_search_kb))
    workflow.add_node("answer_node", RunnableLambda(_answer))

    workflow.add_edge(START, "preprocess_node")
    workflow.add_edge("preprocess_node", "safety_check_node")
    workflow.add_edge("safety_check_node", "classify_intent_node")
    workflow.add_edge("classify_intent_node", "extract_order_id_node")
    workflow.add_edge("extract_order_id_node", "lookup_order_node")
    workflow.add_edge("lookup_order_node", "search_kb_node")
    workflow.add_edge("search_kb_node", "answer_node")
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
            "intent": result.get("intent", intent_rules.DEFAULT_INTENT),
            "order_id": result.get("order_id"),
            "routed_team": result.get("routed_team", "Auto Response"),
            "requires_human": result.get("requires_human", False),
            "answer": result["answer"],
        }
    )
