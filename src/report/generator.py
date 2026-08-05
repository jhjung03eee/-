"""리포트 생성기 - HTML + Markdown"""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.config import get_settings
from src.data.models import ScreeningReport


def format_krw(amount: int | None) -> str:
    if not amount:
        return "미확인"
    if amount >= 10**8:
        return f"{amount / 10**8:.1f}억원"
    if amount >= 10**4:
        return f"{amount / 10**4:.0f}만원"
    return f"{amount:,}원"


def format_krw(amount: int | None) -> str:
    if not amount:
        return "미확인"
    if amount >= 10**8:
        return f"{amount / 10**8:.1f}억원"
    if amount >= 10**4:
        return f"{amount / 10**4:.0f}만원"
    return f"{amount:,}원"


class ReportGenerator:
    def __init__(self):
        self.settings = get_settings()
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        # 필터 등록
        self.env.filters["format_krw"] = format_krw

    def generate(self, report: ScreeningReport, output_path: str, formats: list[str] = None) -> list[str]:
        """리포트 생성"""
        formats = formats or ["html", "md"]
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        generated = []

        if "html" in formats:
            html_path = output_path.with_suffix(".html")
            self._generate_html(report, html_path)
            generated.append(str(html_path))

        if "md" in formats:
            md_path = output_path.with_suffix(".md")
            self._generate_md(report, md_path)
            generated.append(str(md_path))

        return generated

    def _generate_html(self, report: ScreeningReport, output_path: Path):
        template = self.env.get_template("report.html.j2")
        # model_dump()로 dict 변환 후 필터 사용 가능하도록
        data = report.model_dump()
        html = template.render(report=data, format_krw=format_krw)
        output_path.write_text(html, encoding="utf-8")

    def _generate_md(self, report: ScreeningReport, output_path: Path):
        template = self.env.get_template("report.md.j2")
        data = report.model_dump()
        md = template.render(report=data, format_krw=format_krw)
        output_path.write_text(md, encoding="utf-8")