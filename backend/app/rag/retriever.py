from app.rag.store import VectorStore
from app.schemas import RetrievedChunk


class Retriever:
    """Runs a role's query set and merges results, keeping the best score per chunk."""

    def __init__(self, store: VectorStore, top_k: int) -> None:
        self._store = store
        self._top_k = top_k

    async def retrieve(
        self,
        queries: list[str],
        section_boost: tuple[str, ...] = (),
        limit: int | None = None,
    ) -> list[RetrievedChunk]:
        best: dict[str, RetrievedChunk] = {}
        for query in queries:
            for hit in await self._store.search(query, self._top_k, section_boost):
                current = best.get(hit.chunk_id)
                if current is None or hit.score > current.score:
                    best[hit.chunk_id] = hit
        ranked = sorted(best.values(), key=lambda c: -c.score)
        return ranked[: limit or self._top_k]
