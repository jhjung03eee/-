from app.config import Settings, get_settings
from app.llm.base import LLMClient
from app.llm.openai import OpenAIClient
from app.llm.mock import HeuristicClient


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    if settings.live_llm:
        return OpenAIClient(settings)
    return HeuristicClient()
