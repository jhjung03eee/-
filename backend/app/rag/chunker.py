from dataclasses import dataclass

from app.rag.parser import split_sections


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    section: str
    text: str


def chunk_markdown(markdown: str, chunk_size: int = 900, overlap: int = 150) -> list[Chunk]:
    """Section-aware chunking so every chunk carries a citable heading."""
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[Chunk] = []
    for section, body in split_sections(markdown):
        for piece in _split_body(body, chunk_size, overlap):
            chunks.append(Chunk(chunk_id=f"c{len(chunks) + 1:03d}", section=section, text=piece))
    return chunks


def _split_body(body: str, chunk_size: int, overlap: int) -> list[str]:
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    pieces: list[str] = []
    buffer = ""

    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 2 <= chunk_size:
            buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph
            continue
        if buffer:
            pieces.append(buffer)
            buffer = buffer[-overlap:] if overlap else ""
        while len(paragraph) > chunk_size:
            pieces.append(paragraph[:chunk_size])
            paragraph = paragraph[chunk_size - overlap :]
        buffer = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph

    if buffer.strip():
        pieces.append(buffer.strip())
    return pieces
