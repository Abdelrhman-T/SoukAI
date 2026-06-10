import time
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
from tools.cost_tracking import estimate_cost, estimate_latency
from tools.escalation import escalate_to_human
from tools.generate_response import (EmptyResponseError,
                                     ProviderInitializationError,
                                     ResponseGenerationError, draft_response)
from tools.retrieval import extract_order_id, lookup_order, search_kb
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
    intent: str
    intent_confidence: float
    order_id: Optional[str]
    order: Optional[dict[str, Any]]
    kb_matches: list[dict[str, Any]]
    routed_team: str
    requires_human: bool
    provider: str
    model: str
    answer: str
    draft_response_ar: str
    escalation_reason: str
    escalation_priority: str
    input_tokens: int
    output_tokens: int
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
        return {"intent": intent_rules.DEFAULT_INTENT, "intent_confidence" : 0.0}
    intent, intent_confidence = classify_intent(
            state["normalized_text"],
        )
    return {
        "intent": intent,
        "intent_confidence" : intent_confidence
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
            "answer": state["blocked_reason"], # type: ignore
            "draft_response_ar": state["blocked_reason"],
            "input_tokens": 0,
            "output_tokens": 0,
        }

    if not state.get("order_id") and not state.get("injection_detected", False):
        return {
            "provider": provider_name,
            "model": model_name,
            "answer": state["app_settings"].MISSING_ORDER_ID_MESSAGE,
            "draft_response_ar": state["app_settings"].MISSING_ORDER_ID_MESSAGE,
            "input_tokens": 0,
            "output_tokens": 0,
        }

    if state.get("order_id") and not state.get("order"):
        return {
            "provider": provider_name,
            "model": model_name,
            "answer": state["app_settings"].ORDER_NOT_FOUND_MESSAGE,
            "draft_response_ar": state["app_settings"].ORDER_NOT_FOUND_MESSAGE,
            "input_tokens": 0,
            "output_tokens": 0,
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

    escalation_reason = response.get("reason", "")
    escalation_priority = response.get("priority", "")

    if escalation_reason or escalation_priority:
        escalate_to_human(
            reason=escalation_reason,
            priority=escalation_priority,
        )

    return {
        "provider": response["provider"],
        "model": model_name,
        "answer": response["response"],
        "draft_response_ar": response["response"],
        "escalation_reason": escalation_reason,
        "escalation_priority": escalation_priority,
        "input_tokens": response.get("input_tokens", 0),
        "output_tokens": response.get("output_tokens", 0),
    }


def _build_entities(order_id: Optional[str], order: Optional[dict[str, Any]]) -> dict[str, Any]:
    order = order or {}
    return {
        "order_id": order_id,
        "product": order.get("hotel_name"),
        "amount": order.get("room_type"),
        "date": order.get("stay_description"),
    }


def _build_reasoning_trace(result: AgentState) -> list[str]:
    trace = [
        f"normalized_input_script={result.get('script', 'unknown')}",
        f"safety_check={'passed' if result.get('is_safe') else 'blocked'}",
        f"intent={result.get('intent', intent_rules.DEFAULT_INTENT)} confidence={result.get('intent_confidence', 0.0)}",
    ]

    if result.get("order_id"):
        trace.append(f"order_lookup=matched:{result['order_id']}" if result.get("order") else f"order_lookup=not_found:{result['order_id']}")
    else:
        trace.append("order_lookup=missing_order_id")

    trace.append(
        f"routing={result.get('routed_team', 'Auto Response')} human_required={result.get('requires_human', False)}"
    )

    if result.get("escalation_priority"):
        trace.append(
            f"urgency={result.get('escalation_priority')} reason={result.get('escalation_reason', '')}".strip()
        )

    return trace


def _build_tools_used(result: AgentState) -> list[str]:
    tools_used = [
        "normalize_arabic",
        "detect_script",
        "safety_check",
        "classify_intent",
        "extract_order_id",
    ]

    if result.get("order_id"):
        tools_used.append("lookup_order")

    tools_used.append("search_kb")

    if result.get("input_tokens", 0) or result.get("output_tokens", 0):
        tools_used.append("draft_response")

    return tools_used


def _resolve_generation_target(app_settings: Settings) -> tuple[str, str]:
    backend = app_settings.GENERATION_BACKEND.upper()

    if backend == LLMEnums.GROQ.value:
        return LLMEnums.GROQ.value, app_settings.GROQ_MODEL

    if backend == LLMEnums.OPENROUTER.value:
        return LLMEnums.OPENROUTER.value, app_settings.OPENROUTER_MODEL

    raise ProviderInitializationError(
        f"Unsupported generation backend: {app_settings.GENERATION_BACKEND}"
    )


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
    start_time = time.perf_counter()
    graph = _graph_factory()
    provider_name, model_name = _resolve_generation_target(app_settings)

    try:
        result = graph.invoke(
            {
                "text": request.text,
                "provider": provider_name,
                "model": model_name,
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

    latency_ms = estimate_latency(start_time, time.perf_counter())

    return JSONResponse(
        content={
        "intent": result.get("intent", intent_rules.DEFAULT_INTENT),
        "intent_confidence": result.get("intent_confidence", 0.0),
        "urgency": result.get("escalation_priority") or "low",
        "entities": _build_entities(
            result.get("order_id"),
            result.get("order"),
        ),
        "requires_human": result.get("requires_human", False),
        "routed_team": result.get("routed_team", "Auto Response"),
        "draft_response_ar": result.get("draft_response_ar", result.get("answer", "")),
        "reasoning_trace": _build_reasoning_trace(result),
        "tools_used": _build_tools_used(result),
        "latency_ms": latency_ms,
        "est_cost_usd": estimate_cost(int(result.get("input_tokens", 0) or 0), int(result.get("output_tokens", 0) or 0)),
        }
    )
