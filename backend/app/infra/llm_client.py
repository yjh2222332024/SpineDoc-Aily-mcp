"""
LLM Client Factory — single source of truth for AsyncOpenAI client creation.

Replace all ad-hoc `AsyncOpenAI(api_key=..., base_url=...)` with `get_llm_client()`.
"""
from openai import AsyncOpenAI
from backend.app.core.config import settings

_client = None


def get_llm_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
    return _client
