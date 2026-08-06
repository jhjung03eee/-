"""Vercel entry point - exports FastAPI app from api/index.py"""

from api.index import app

# Export for Vercel
__all__ = ["app"]