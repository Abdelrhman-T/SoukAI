from helpers.config import Settings, getSettings
from stores.LLMEnums import LLMEnums

settings = getSettings()

def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    
    if settings.GENERATION_BACKEND == LLMEnums.GROQ.value:
        pricing = [settings.GROQ_INPUT_PER_1K, settings.GROQ_OUTPUT_PER_1K]
    elif settings.GENERATION_BACKEND == LLMEnums.OPENROUTER.value:
        pricing = [settings.OPENROUTER_INPUT_PER_1K, settings.OPENROUTER_OUTPUT_PER_1K]
    else:
        pricing = [0.0,0.0]
    return round(
        (input_tokens / 1000.0) * pricing[0]
        + (output_tokens / 1000.0) * pricing[1],
        6,
    )


def estimate_latency(start_time: float, end_time: float) -> float:
    return round((end_time - start_time) * 1000.0, 2)
