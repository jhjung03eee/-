"""Vercel serverless entrypoint: exposes the FastAPI ASGI app under /api/*."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402

__all__ = ["app"]
