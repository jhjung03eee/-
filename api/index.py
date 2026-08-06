"""Vercel Serverless Function Entry Point for KIA Bid Screener.

This serves both the API endpoints and the frontend static files.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.config import get_settings
from src.data.loader import load_company, load_corpus
from src.data.models import ScreeningReport, ScreeningResult
from src.engine import (
    calculate_score,
    calculate_risk_penalty,
    get_key_risks,
    match_qualifications,
    prefilter,
)
from src.llm import get_client
from src.report import ReportGenerator

# FastAPI app
app = FastAPI(
    title="KIA Bid Screener API",
    description="공공 입찰공고 자동 스크리닝 API",
    version="0.1.0",
)

# Settings
settings = get_settings()

# Vercel uses read-only filesystem - use /tmp for output
def get_output_path() -> Path:
    """Get writable output path (uses /tmp on Vercel)"""
    if os.environ.get("VERCEL"):
        return Path("/tmp") / "reports"
    return settings.output_path

# Ensure output directory exists (only locally)
if not os.environ.get("VERCEL"):
    settings.output_path.mkdir(parents=True, exist_ok=True)


# Request/Response Models
class ScreenRequest(BaseModel):
    date: str | None = None
    category: str | None = None
    format: str = "html,md"


class ScreenResponse(BaseModel):
    success: bool
    message: str
    report_url: str | None = None
    stats: dict | None = None


class HealthResponse(BaseModel):
    status: str
    llm_mode: str
    model: str


# API Endpoints
@app.get("/api/health", response_model=HealthResponse)
async def health():
    """헬스 체크 및 현재 LLM 모드 확인"""
    return HealthResponse(
        status="ok",
        llm_mode="live" if settings.live_llm else "offline (heuristic)",
        model=settings.openai_model,
    )


@app.get("/api/config")
async def get_config():
    """설정 정보 조회 (마스킹된 API 키)"""
    return {
        "corpus_dir": str(settings.corpus_path),
        "output_dir": str(settings.output_path),
        "min_project_budget": settings.min_project_budget,
        "strong_threshold": settings.strong_threshold,
        "review_threshold": settings.review_threshold,
        "llm_live": settings.live_llm,
        "model": settings.openai_model,
    }


@app.get("/api/corpus")
async def get_corpus():
    """코퍼스 공고 목록 조회"""
    records = load_corpus(settings.corpus_path)
    company = load_company(settings.corpus_path)

    return {
        "total": len(records),
        "company": company.name,
        "bids": [
            {
                "bid_id": r.bid_id,
                "title": r.title,
                "category": r.category,
                "agency": r.agency,
                "budget": r.budget,
                "deadline": r.deadline.isoformat() if r.deadline else None,
            }
            for r in records
        ],
    }


@app.post("/api/screen", response_model=ScreenResponse)
async def screen_bids(request: ScreenRequest):
    """배치 스크리닝 실행"""
    from datetime import date, datetime
    import asyncio

    # 기준일 파싱
    if request.date:
        try:
            today = datetime.strptime(request.date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="날짜 형식: YYYY-MM-DD")
    else:
        today = date.today()

    # 카테고리 필터
    cat_filter = [c.strip() for c in request.category.split(",")] if request.category else None

    # LLM 클라이언트
    llm_client = get_client() if settings.live_llm else None

    # 데이터 로드
    records = load_corpus(settings.corpus_path)
    company = load_company(settings.corpus_path)

    if cat_filter:
        records = [r for r in records if r.category in cat_filter]

    # 스크리닝 실행
    results = []
    for record in records:
        pf = prefilter(record, company, today)
        quals = await match_qualifications(record, company, llm_client)

        qual_pass = all(
            m.status in ("충족", "부분충족")
            for m in quals
            if "해당시" not in m.requirement and "공동도급" not in m.requirement and "중소기업" not in m.requirement
        )

        risks = get_key_risks(record)
        score, breakdown, reason = calculate_score(record, company, quals, pf)

        if score >= settings.strong_threshold:
            grade = "적극추천"
        elif score >= settings.review_threshold:
            grade = "검토"
        else:
            grade = "패스"

        result = ScreeningResult(
            bid_id=record.bid_id,
            title=record.title,
            category=record.category,
            agency=record.agency,
            budget=record.budget,
            deadline=record.deadline,
            days_left=pf.days_left,
            urgent=pf.urgent,
            prefilter_blocked=pf.blocked,
            prefilter_reasons=pf.reasons,
            qualification_matches=quals,
            qualification_pass=qual_pass and not pf.blocked,
            score=score,
            grade=grade,
            reason=reason,
            breakdown=breakdown,
            risks=risks,
        )
        results.append(result)

    # 정렬
    tier_order = {"적극추천": 0, "검토": 1, "패스": 2}
    results.sort(key=lambda r: (tier_order[r.grade], r.days_left if r.days_left is not None else 999, -r.score))

    # 통계
    counts = {"적극추천": 0, "검토": 0, "패스": 0}
    for r in results:
        counts[r.grade] += 1
    filtered_out = sum(1 for r in results if r.prefilter_blocked)
    screened_count = len(results) - filtered_out

    # 리포트 생성
    report = ScreeningReport(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        corpus=str(settings.corpus_path),
        company=company.name,
        total=len(results),
        filtered_out=filtered_out,
        screened_count=screened_count,
        counts=counts,
        screening_items=results,
        total_latency_ms=0,
    )

    generator = ReportGenerator()
    formats = [f.strip() for f in request.format.split(",")]
    
    # Use temp directory for Vercel
    output_dir = get_output_path()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    generated = generator.generate(report, output_path, formats)

    # Read generated HTML content to return directly (Vercel can't serve static files)
    html_content = None
    for f in generated:
        if f.endswith(".html"):
            html_content = Path(f).read_text(encoding="utf-8")
            break
    
    report_url = None
    if html_content:
        # On Vercel, return base64 encoded HTML or just the content
        import base64
        report_url = f"data:text/html;base64,{base64.b64encode(html_content.encode()).decode()}"

    return ScreenResponse(
        success=True,
        message=f"스크리닝 완료: {len(results)}건 처리",
        report_url=report_url,
        stats={
            "total": len(results),
            "counts": counts,
            "filtered_out": filtered_out,
        },
    )


# Catch-all for SPA (if frontend exists)
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists() and not os.environ.get("VERCEL"):
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


# For local development
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)