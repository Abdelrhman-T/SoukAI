import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from helpers.config import Settings, getSettings
from stores.LLMEnums import LLMEnums
from stores.LLMProviderFactory import LLMProviderFactory

base_router = APIRouter(prefix="/api/v1", tags=["api_v1"])
nlp_router = APIRouter(prefix="/api/v1/nlp", tags=["api_v1", "nlp"])
logger = logging.getLogger(__name__)


class AnswerRequest(BaseModel):
    text: str


@base_router.get("/")
async def welcome(app_setting: Settings = Depends(getSettings)):

    app_name = app_setting.APP_NAME
    app_version = app_setting.APP_VERSION
    return {"APP_NAME": app_name, "APP_VERSION": app_version}


@nlp_router.post("/answer")
async def answer_rag(
    request: AnswerRequest,
    app_setting: Settings = Depends(getSettings),
):
    prompt = request.text.strip()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="`text` must not be empty.",
        )
    settings = app_setting

    Model_Name = LLMEnums.GROQ.value
    Model_ID = app_setting.GROQ_MODEL

    ProviderFactory = LLMProviderFactory(settings)
    provider = ProviderFactory.create(Model_Name)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize provider.",
        )

    try:
        answer = provider.generate_text(
            prompt=prompt,
            chat_history=[],
            max_output_tokens=app_setting.DEFAULT_MAX_OUTPUT_TOKENS,
            temperature=app_setting.DEFAULT_TEMPERATURE,
        )
    except Exception as exc:
        logger.exception(f"{Model_Name} generation failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{Model_Name} request failed.",
        ) from exc

    if not answer:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{Model_Name} returned an empty response.",
        )

    return JSONResponse(
        content={
            "provider": Model_Name,
            "model": Model_ID,
            "text": prompt,
            "answer": answer,
        }
    )
