import json
import re
from typing import Callable, Protocol

StructuredFallback = Callable[[], dict]

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class LLMClient(Protocol):
    name: str

    async def structured(self, system: str, user: str, fallback: StructuredFallback) -> dict:
        """Return a JSON object from the model, falling back to a deterministic heuristic."""


def parse_json_object(raw: str) -> dict:
    """Extract the first JSON object from a model response."""
    candidates = [raw.strip()]
    block = _JSON_BLOCK.search(raw)
    if block:
        candidates.insert(0, block.group(1).strip())

    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        candidates.append(raw[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("no JSON object found in model response")
