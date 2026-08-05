import numpy as np

from app.rag.chunker import Chunk
from app.rag.embeddings import Embeddings
from app.schemas import RetrievedChunk


class VectorStore:
    def __init__(self, embeddings: Embeddings) -> None:
        self._embeddings = embeddings
        self._chunks: list[Chunk] = []
        self._matrix: np.ndarray | None = None

    @property
    def chunks(self) -> list[Chunk]:
        return list(self._chunks)

    async def index(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks
        self._matrix = await self._embeddings.embed([c.text for c in chunks]) if chunks else None

    async def search(
        self,
        query: str,
        top_k: int,
        section_boost: tuple[str, ...] = (),
    ) -> list[RetrievedChunk]:
        if self._matrix is None or not self._chunks:
            return []

        query_vector = (await self._embeddings.embed([query]))[0]
        scores = self._matrix @ query_vector

        if section_boost:
            for i, chunk in enumerate(self._chunks):
                if any(keyword in chunk.section for keyword in section_boost):
                    scores[i] += 0.15

        ranked = np.argsort(-scores)[:top_k]
        return [
            RetrievedChunk(
                chunk_id=self._chunks[i].chunk_id,
                section=self._chunks[i].section,
                text=self._chunks[i].text,
                score=round(float(scores[i]), 4),
            )
            for i in ranked
            if scores[i] > 0
        ]
