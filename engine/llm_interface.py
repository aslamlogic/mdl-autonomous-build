import os
from engine.openai_provider import generate_code_openai


def generate_code(spec: dict) -> str:
    """
    Entry point for code generation.
    Abstracted interface — currently OpenAI only.
    """

    provider = os.getenv("LLM_PROVIDER", "openai")

    if provider == "openai":
        return generate_code_openai(spec)

    raise ValueError(f"Unsupported LLM provider: {provider}")
