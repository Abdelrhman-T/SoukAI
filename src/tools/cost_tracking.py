from helpers.config import Settings


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    
    if Settings.GENERATION_BACKEND == "GROQ":
        pricing = [Settings.GROQ_INPUT_PER_1K, Settings.GROQ_OUTPUT_PER_1K]
    elif Settings.GENERATION_BACKEND == "OPENROUTER":
        pricing = [Settings.OPENROUTER_INPUT_PER_1K, Settings.OPENROUTER_OUTPUT_PER_1K]
    else:
        pricing = [0.0,0.0]
    return round(
        (input_tokens / 1000.0) * pricing[0]
        + (output_tokens / 1000.0) * pricing[1],
        6,
    )


def estimate_latency(start_time: float, end_time: float) -> float:
    return round((end_time - start_time) * 1000.0, 2)
