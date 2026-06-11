from abc import ABC, abstractmethod
from typing import List


class LLMInterface(ABC):

    @abstractmethod
    def set_generation_model(self, model_id: str):
        pass

    @abstractmethod
    def set_embedding_model(self, model_id: str, embedding_size: int):
        pass

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        chat_history: list = [],
        max_output_tokens: int = 200,
        temperature: float = 0.1,
    ) -> (str | None):
        pass

    @abstractmethod
    def embed_text(self, text, document_type: str = "") -> (List[float] | None):
        pass

    @abstractmethod
    def construct_prompt(self, prompt: str, role: str) -> dict:
        pass
