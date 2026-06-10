import logging
from typing import List, Union

from groq import Groq

from ..LLMEnums import qroqEnums
from ..LLMInterface import LLMInterface


class groqProvider(LLMInterface):
    def __init__(
        self,
        enum,
        api_key: str,
        default_input_max_characters: int = 1000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1,
    ):
        self.api_key = api_key

        self.enum = enum

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None
        self.embed_model_id = None
        self.embedding_size = None

        self.client = Groq(api_key=self.api_key) if Groq and self.api_key else None

        self.enums = qroqEnums
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
            self.logger.error("groq client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for qroq was not set")
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
            self.construct_prompt(prompt=prompt, role=qroqEnums.USER.value)
        )

        response = self.client.chat.completions.create(
            model=self.generation_model_id,
            messages=chat_history,
            max_completion_tokens=max_output_tokens,
            temperature=temperature,
        )

        if (
            not response
            or not response.choices
            or len(response.choices) == 0
            or not response.choices[0]
        ):
            self.logger.error("Error while generating text with qroq")
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

    def embed_text(self, text: Union[str, List[str]], document_type=None):
        raise ValueError("There no embed_text in qroq")
