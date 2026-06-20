
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from helpers.config import Settings, getSettings
from routes.agent import run_agent_text
from tools.facebook_client import FacebookClient

webhook_router = APIRouter(prefix="/api/v1/meta", tags=["meta-webhook"])
logger = logging.getLogger(__name__)

@webhook_router.get("/webhook")
async def verify_webhook(
    request: Request,
    app_settings: Settings = Depends(getSettings),
):
    params = request.query_params
    logger.warning("META WEBHOOK VERIFY params=%s", dict(params))

    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == app_settings.META_VERIFY_TOKEN:
        return PlainTextResponse(content=challenge or "")

    raise HTTPException(status_code=403, detail="Invalid verify token")


@webhook_router.post("/webhook")
async def receive_webhook(
    request: Request,
    app_settings: Settings = Depends(getSettings),
):
    raw_body = await request.body()
    raw_text = raw_body.decode("utf-8", errors="replace")

    logger.warning("META WEBHOOK POST headers=%s body=%s", dict(request.headers), raw_text)

    try:
        body = json.loads(raw_text) if raw_text else {}
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode webhook body as JSON")
        raise HTTPException(status_code=400, detail="Invalid webhook JSON body") from exc

    results = []
    skipped_events = []

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            if value.get("item") != "comment":
                skipped_events.append(
                    {
                        "reason": "item_not_comment",
                        "item": value.get("item"),
                        "field": change.get("field"),
                    }
                )
                continue

            if value.get("verb") != "add":
                skipped_events.append(
                    {
                        "reason": "verb_not_add",
                        "verb": value.get("verb"),
                        "field": change.get("field"),
                    }
                )
                continue

            comment_id = value.get("comment_id")
            comment_text = value.get("message")

            author_id = value.get("from", {}).get("id")
            if app_settings.FACEBOOK_PAGE_ID and author_id == app_settings.FACEBOOK_PAGE_ID:
                skipped_events.append(
                    {
                        "reason": "self_authored_comment",
                        "comment_id": comment_id,
                        "author_id": author_id,
                    }
                )
                continue

            if not comment_id or not comment_text:
                skipped_events.append(
                    {
                        "reason": "missing_comment_payload",
                        "comment_id": comment_id,
                        "has_message": bool(comment_text),
                    }
                )
                continue

            agent_result = run_agent_text(
                text=comment_text,
                app_settings=app_settings,
            )

            reply_text = agent_result["draft_response_ar"]

            facebook = FacebookClient(app_settings)
            facebook_result = facebook.reply_to_comment(
                comment_id=comment_id,
                message=reply_text,
            )

            results.append({
                "comment_id": comment_id,
                "reply_text": reply_text,
                "agent": agent_result,
                "facebook": facebook_result,
            })

    return {
        "status": "processed",
        "count": len(results),
        "skipped_events": skipped_events,
        "results": results,
    }


@webhook_router.get("/facebook/pages/{page_id}/posts")
async def get_facebook_page_posts(
    page_id: str,
    limit: int = Query(default=25, ge=1, le=100),
    app_settings: Settings = Depends(getSettings),
):
    facebook = FacebookClient(app_settings)
    return facebook.get_page_posts(page_id=page_id, limit=limit)


@webhook_router.get("/facebook/pages/{page_id}/posts/all")
async def get_all_facebook_page_posts(
    page_id: str,
    limit: int = Query(default=25, ge=1, le=100),
    max_pages: int = Query(default=10, ge=1, le=50),
    app_settings: Settings = Depends(getSettings),
):
    facebook = FacebookClient(app_settings)
    posts = facebook.get_all_page_posts(
        page_id=page_id,
        limit=limit,
        max_pages=max_pages,
    )

    return {
        "page_id": page_id,
        "count": len(posts),
        "posts": posts,
    }


@webhook_router.get("/facebook/posts/{post_id}/comments")
async def get_facebook_post_comments(
    post_id: str,
    limit: int = Query(default=100, ge=1, le=100),
    app_settings: Settings = Depends(getSettings),
):
    facebook = FacebookClient(app_settings)
    return facebook.get_post_comments(post_id=post_id, limit=limit)

