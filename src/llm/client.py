"""Elice LLM 클라이언트 (OpenAI-compatible)"""

from openai import AsyncOpenAI
from src.config import get_settings

_settings = get_settings()

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=_settings.openai_api_key,
            base_url=_settings.openai_base_url,
            timeout=_settings.llm_timeout_seconds,
        )
    return _client


async def structured_completion(
    prompt: str,
    response_model: type,
    temperature: float | None = None,
) -> object:
    """구조화된 출력으로 LLM 호출"""
    client = get_client()
    response = await client.beta.chat.completions.parse(
        model=_settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        response_format=response_model,
        temperature=temperature if temperature is not None else _settings.llm_temperature,
    )
    return response.choices[0].message.parsed


async def simple_completion(prompt: str, temperature: float | None = None) -> str:
    """단순 텍스트 출력"""
    client = get_client()
    response = await client.chat.completions.create(
        model=_settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature if temperature is not None else _settings.llm_temperature,
    )
    return response.choices[0].message.content or ""