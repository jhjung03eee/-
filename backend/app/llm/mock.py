from app.llm.base import StructuredFallback


class HeuristicClient:
    """Offline provider: runs the same rule-based reasoning the live client falls back to.

    Keeps the whole workflow demoable and tests deterministic without an API key.
    """

    name = "heuristic-offline"

    async def structured(self, system: str, user: str, fallback: StructuredFallback) -> dict:
        return fallback()
