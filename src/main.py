"""KIA 입찰공고 스크리너 - CLI 메인"""

import asyncio
from datetime import date, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

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

app = typer.Typer(
    name="kia-bid-screener",
    help="KIA 공공입찰 공고 자동 스크리너",
    no_args_is_help=True,
)
console = Console()


@app.command()
def screen(
    date: str = typer.Option(None, "--date", "-d", help="기준일 (YYYY-MM-DD, 기본값: 오늘)"),
    output: str = typer.Option("report.html", "--output", "-o", help="출력 파일 경로"),
    format: str = typer.Option("html,md", "--format", "-f", help="출력 포맷 (html,md)"),
    category: str = typer.Option(None, "--category", "-c", help="카테고리 필터 (콤마구분)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="상세 로그"),
):
    """배치 스크리닝 실행"""
    settings = get_settings()

    # 기준일 파싱
    if date:
        try:
            today = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            console.print("[red]날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력하세요.[/red]")
            raise typer.Exit(1)
    else:
        today = date.today()

    # 카테고리 필터 파싱
    cat_filter = [c.strip() for c in category.split(",")] if category else None

    console.print(f"[bold blue]KIA 입찰공고 스크리닝 시작[/bold blue]")
    console.print(f"기준일: {today}")
    console.print(f"데이터: {settings.corpus_path}")
    console.print(f"LLM 모드: {'라이브' if settings.live_llm else '오프라인(휴리스틱)'}")

    # LLM 클라이언트 준비
    llm_client = get_client() if settings.live_llm else None

    async def run_screening():
        # 1. 데이터 로드
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            load_task = progress.add_task("데이터 로드 중...", total=None)
            records = load_corpus(settings.corpus_path)
            company = load_company(settings.corpus_path)
            progress.update(load_task, completed=True, description=f"데이터 로드 완료: {len(records)}건")

            # 카테고리 필터 적용
            if cat_filter:
                records = [r for r in records if r.category in cat_filter]
                console.print(f"카테고리 필터 적용: {cat_filter} → {len(records)}건")

            # 2. 각 공고 처리
            results = []
            screen_task = progress.add_task("스크리닝 중...", total=len(records))

            for record in records:
                # 사전 필터
                pf = prefilter(record, company, today)

                # 자격요건 매칭
                quals = await match_qualifications(record, company, llm_client)

                # 자격 통과 여부 (필수요건 모두 충족)
                qual_pass = all(
                    m.status in ("충족", "부분충족")
                    for m in quals
                    if "해당시" not in m.requirement and "공동도급" not in m.requirement and "중소기업" not in m.requirement
                )

                # 리스크
                risks = get_key_risks(record)

                # 스코어링
                score, breakdown, reason = calculate_score(record, company, quals, pf)

                # 등급
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
                progress.advance(screen_task)

            # 3. 정렬 (적극추천 > 검토 > 패스, 같은 등급이면 마감임박 순)
            tier_order = {"적극추천": 0, "검토": 1, "패스": 2}
            results.sort(key=lambda r: (tier_order[r.grade], r.days_left if r.days_left is not None else 999, -r.score))

            # 4. 통계
            counts = {"적극추천": 0, "검토": 0, "패스": 0}
            for r in results:
                counts[r.grade] += 1

            filtered_out = sum(1 for r in results if r.prefilter_blocked)
            screened_count = len(results) - filtered_out

            # 5. 리포트 생성
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

            gen_task = progress.add_task("리포트 생성 중...", total=None)
            generator = ReportGenerator()
            formats_list = [f.strip() for f in format.split(",")]
            generated_files = generator.generate(report, output, formats_list)
            progress.update(gen_task, completed=True, description="리포트 생성 완료")

        # 결과 요약 출력
        console.print(f"\n[bold green]스크리닝 완료![/bold green]")
        console.print(f"  적극추천: {counts['적극추천']}건")
        console.print(f"  검토: {counts['검토']}건")
        console.print(f"  패스: {counts['패스']}건")
        console.print(f"  사전필터 제외: {filtered_out}건")
        console.print(f"\n출력 파일: {', '.join(generated_files)}")

        # 상위 5개 적극추천/검토 간단 출력
        top_items = [r for r in results if r.grade in ("적극추천", "검토")][:5]
        if top_items:
            console.print("\n[bold]주요 추천 건:[/bold]")
            for item in top_items:
                urgent_mark = " ⚠️" if item.urgent else ""
                console.print(f"  {item.grade} | {item.title} ({item.budget/1e8:.1f}억) | {item.reason}{urgent_mark}")

    asyncio.run(run_screening())


@app.command()
def check_env():
    """환경변수/설정 검증"""
    settings = get_settings()
    console.print("[bold]설정 확인:[/bold]")
    console.print(f"  Corpus: {settings.corpus_path} {'✓' if settings.corpus_path.exists() else '✗'}")
    console.print(f"  Output: {settings.output_path}")
    console.print(f"  LLM Live: {settings.live_llm}")
    console.print(f"  Model: {settings.openai_model}")
    console.print(f"  Base URL: {settings.openai_base_url}")
    console.print(f"  API Key: {'설정됨' if settings.openai_api_key else '미설정'}")


if __name__ == "__main__":
    app()