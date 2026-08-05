"""Single-document review reads from the same corpus the batch screener uses."""

from app.config import get_settings
from app.screening.dataset import load_corpus


def _records():
    root = get_settings().corpus_path
    return load_corpus(root) if root.is_dir() else []


def list_samples() -> list[dict]:
    return [
        {"id": record.bid_id, "title": record.facts().title, "filename": record.source}
        for record in _records()
    ]


def load_sample(sample_id: str) -> str | None:
    return next((r.markdown for r in _records() if r.bid_id == sample_id), None)
