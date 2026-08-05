from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AI Go/No-Go Review Committee",
    description="공공 입찰공고에 대한 멀티 에이전트 참여 여부 심의 시스템",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root() -> dict:
    return {"service": "go-no-go-committee", "docs": "/docs"}
