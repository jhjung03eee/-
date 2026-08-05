"""Vercel serverless entrypoint: exposes the FastAPI ASGI app under /api/* and
serves the built frontend (frontend/dist) for every other path.

Vercel's FastAPI auto-detection routes ALL paths to this app once a
Python function is present, bypassing static file hosting entirely, so
the SPA has to be served from here instead of `outputDirectory`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from app.main import app  # noqa: E402

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

# Drop app.main's own "/" route so the SPA's index.html can take over.
app.router.routes = [route for route in app.router.routes if getattr(route, "path", None) != "/"]

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str) -> FileResponse:
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")


__all__ = ["app"]
