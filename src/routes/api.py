import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from helpers.config import Settings, getSettings
from stores.LLMEnums import LLMEnums
from tools import arabic_utils
from tools.generate_response import (EmptyResponseError, Prompt,
                                     PromptValidationError,
                                     ProviderInitializationError,
                                     ResponseGenerationError, llm_response)

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
    user_prompt = arabic_utils.normalize_arabic(request.text)

    print(user_prompt)

    if not user_prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="`text` must not be empty.",
        )
    

    Model_Name = LLMEnums.GROQ.value
    Model_ID = app_setting.GROQ_MODEL
    prompt = Prompt(sys_prompt="", user_prompt=user_prompt)


    try:
        response = llm_response(
            provider_name=Model_Name,
            prompt=prompt,
            app_settings=app_setting,
        )
    except PromptValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
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

    return JSONResponse(
        content={
            "provider": response["provider"],
            "model": Model_ID,
            "text": user_prompt,
            "answer": response["answer"],
        }
    )
