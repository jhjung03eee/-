import logging

import httpx

from app.config import Settings
from app.llm.base import StructuredFallback, parse_json_object

logger = logging.getLogger(__name__)


class GLMClient:
    """GLM 5.2 chat completions over the OpenAI-compatible BigModel endpoint."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.name = f"glm:{settings.glm_model}"

    async def structured(self, system: str, user: str, fallback: StructuredFallback) -> dict:
        payload = {
            "model": self._settings.glm_model,
            "temperature": self._settings.llm_temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self._settings.glm_api_key}"}

        try:
            async with httpx.AsyncClient(timeout=self._settings.llm_timeout_seconds) as client:
                response = await client.post(
                    f"{self._settings.glm_base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            return parse_json_object(content)
        except Exception:
            logger.exception("GLM call failed; using heuristic fallback")
            result = fallback()
            result["degraded"] = True
            return result
