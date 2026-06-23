import logging
from functools import lru_cache
from typing import Any

from supabase import Client, create_client

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase_client(supabase_url: str, supabase_key: str) -> Client:
    return create_client(supabase_url, supabase_key)


def save_evaluation_to_supabase(row: dict[str, Any], app_settings) -> None:
    supabase_url = getattr(app_settings, "SUPABASE_URL", None)
    supabase_key = getattr(app_settings, "SUPABASE_SERVICE_ROLE_KEY", None)

    if not supabase_url or not supabase_key:
        logger.warning("Supabase credentials are missing. Evaluation row was not saved.")
        return

    payload = {
        "evaluated_at": row.get("evaluated_at"),
        "evaluation_provider": row.get("evaluation_provider"),
        "evaluation_model": row.get("evaluation_model"),
        "customer_message": row.get("customer_message"),
        "predicted_intent": row.get("predicted_intent"),
        "routed_team": row.get("routed_team"),
        "generated_response": row.get("generated_response"),
        "evaluation_status": row.get("evaluation_status"),
        "evaluation_time_ms": row.get("evaluation_time_ms"),
        "correctness": row.get("correctness"),
        "helpfulness": row.get("helpfulness"),
        "dialect_match": row.get("dialect_match"),
        "tone": row.get("tone"),
        "overall_score": row.get("overall_score"),
        "passed": row.get("pass") if "pass" in row else row.get("passed"),
        "failure_category": row.get("failure_category"),
        "short_reason": row.get("short_reason"),
        "judge_input_tokens": row.get("judge_input_tokens", 0),
        "judge_output_tokens": row.get("judge_output_tokens", 0),
        "evaluation_error": row.get("evaluation_error"),
    }

    try:
        client = get_supabase_client(supabase_url, supabase_key)
        client.table("runtime_response_evaluations").insert(payload).execute()
    except Exception:
        logger.exception("Failed to save evaluation row to Supabase.")