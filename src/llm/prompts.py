"""LLM 프롬프트 템플릿"""

QUALIFICATION_PROMPT = """
당신은 KIA 입찰담당자입니다. 다음 입찰 자격요건을 KIA의 보유 자격과 대조하여 판단하세요.

[입찰 자격요건]
{requirement}

[KIA 보유 자격/실적/인력 요약]
- 면허/인증: {licenses}
- 수행실적: {track_records_summary}
- 기술인력: {tech_staff_summary}

[판단 기준]
- "충족": 명시적 요건을 KIA가 명확히 만족 (면허명 일치, 실적 건수/규모 충족, 인력 수 충족 등)
- "부분충족": 일부 만족하나 추가 확인/보완 필요 (예: 실적 1건만, 중소기업 해당 여부 불확실 등)
- "미충족": KIA가 해당 요건을 만족하지 못함 (입찰 불가 사유가 되는 필수 요건 미달)
- "확인불가": 제공된 정보만으로 판단 불가 (해당 분야 실적 있는지 모름 등)

JSON만 출력하세요:
{{
  "status": "충족|부분충족|미충족|확인불가",
  "evidence": "판단 근거 (KIA 보유 내역 인용)",
  "kia_evidence": "매칭되는 KIA 구체적 증빙"
}}
""".strip()


def build_qualification_prompt(requirement: str, company) -> str:
    licenses = ", ".join(company.licenses[:15])
    track_summary = "; ".join(
        f"{tr.category}: {tr.project_name}({tr.amount_display})"
        for tr in company.track_records[:8]
    )
    tech_staff = ""
    if company.technical_staff:
        tech_staff = f"{company.technical_staff.count}명 (고급 {company.technical_staff.senior_above}명: " + ", ".join(
            f"{k}{v}명" for k, v in list(company.technical_staff.breakdown.items())[:5]
        ) + ")"

    return QUALIFICATION_PROMPT.format(
        requirement=requirement,
        licenses=licenses,
        track_records_summary=track_summary,
        tech_staff_summary=tech_staff,
    )