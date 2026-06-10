import logging
from enum import Enum
from typing import List, Union

from openai import OpenAI

from ..LLMEnums import openrouterEnums
from ..LLMInterface import LLMInterface


class openrouterProvider(LLMInterface):
    def __init__(
        self,
        enum,
        api_key: str,
        api_url: str = "",
        default_input_max_characters: int = 1000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1,
    ):
        self.api_key = api_key
        self.api_url = api_url

        self.enum = enum

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None
        self.embed_model_id = None
        self.embedding_size = None

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_url if self.api_url and len(self.api_url) else None,
        )
        
        self.enums = openrouterEnums
        self.logger = logging.getLogger(__name__)


    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embed_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        return text[0 : self.default_input_max_characters].strip()

    def construct_prompt(self, prompt: str, role: str):
        return {"role": role, "content": prompt}

    def generate_text(
        self,
        prompt: str,
        chat_history: list = [],
        max_output_tokens: int = 200,
        temperature: float = 0.1,
    ):
        if not self.client:
            self.logger.error("OpenRouter client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for OpenRouter was not set")
            return None

        max_output_tokens = (
            max_output_tokens
            if max_output_tokens
            else self.default_generation_max_output_tokens
        )
        temperature = (
            temperature if temperature else self.default_generation_temperature
        )

        chat_history.append(
            self.construct_prompt(prompt=prompt, role=openrouterEnums.USER.value)
        )

        response = self.client.chat.completions.create(
            model=self.generation_model_id,
            messages=chat_history,
            max_tokens=max_output_tokens,
            temperature=temperature,
            extra_body={"reasoning": {"enabled": False}}
        )

        if (
            not response
            or not response.choices
            or len(response.choices) == 0
            or not response.choices[0]
        ):
            self.logger.error("Error while generating text with OpenRouter")
            return None

        usage = getattr(response, "usage", None)

        return {
            "text": response.choices[0].message.content,
            "usage": {
                "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
                "output_tokens": getattr(usage, "completion_tokens", 0)
                if usage
                else 0,
            },
        }

    def embed_text(self, text: Union[str, List[str]], document_type: str = ""):
        if not self.client:
            self.logger.error("OpenRouter client was not set")
            return None

        if not self.embed_model_id:
            self.logger.error("Embedding model for OpenRouter was not set")
            return None

        if isinstance(text, str):
            text = [text]

        response = self.client.embeddings.create(
            model=self.embed_model_id, input=[self.process_text(t) for t in text]
        )

        if (
            not response
            or not response.data
            or len(response.data) == 0
            or not response.data[0]
        ):
            self.logger.error("Error while embedding text with OpenRouter")
            return None

        return response.data[0].embedding
