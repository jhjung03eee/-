"""자격요건 매칭 엔진 - 규칙 1차 + LLM 2차 하이브리드"""

import logging
from typing import TYPE_CHECKING

from src.data.models import BidRecord, CompanyProfile, QualificationMatch
from src.llm.heuristics import heuristic_qualification_match

if TYPE_CHECKING:
    from src.llm.client import AsyncOpenAI

logger = logging.getLogger(__name__)


async def match_qualifications(
    record: BidRecord,
    company: CompanyProfile,
    llm_client: "AsyncOpenAI | None" = None,
) -> list[QualificationMatch]:
    """
    자격요건 매칭:
    1. 규칙 기반 1차 판단 (확실한 경우만)
    2. 애매한 경우 LLM 호출
    3. LLM 실패 시 휴리스틱 폴백
    """
    results = []

    for req in record.qualifications:
        # 1단계: 규칙 기반 빠른 판단
        rule_result = _rule_based_match(req, company)
        if rule_result.status in ("충족", "미충족"):
            results.append(rule_result)
            continue

        # 2단계: LLM 판단 시도
        if llm_client:
            try:
                llm_result = await _llm_match(req, company, llm_client)
                results.append(llm_result)
                continue
            except Exception as e:
                logger.warning(f"LLM 매칭 실패, 휴리스틱 폴백: {e}")

        # 3단계: 휴리스틱 폴백
        heuristic_results = heuristic_qualification_match(record, company)
        # 해당 요건에 대한 휴리스틱 결과 찾기
        for hr in heuristic_results:
            if hr.requirement == req:
                results.append(hr)
                break
        else:
            results.append(QualificationMatch(
                requirement=req,
                status="확인불가",
                evidence="자동 판단 불가",
                kia_evidence="",
            ))

    return results


def _rule_based_match(req: str, company: CompanyProfile) -> QualificationMatch:
    """확실한 규칙 기반 매칭"""
    req_lower = req.lower()
    kia_licenses = set(company.licenses)

    # 면허/인증 직접 매칭
    license_map = {
        "소프트웨어사업자": ["소프트웨어사업", "일반소프트웨어개발", "정보처리시스템설계"],
        "정보통신공사업": ["정보통신공사"],
        "전자계산조직응용사업": ["전자계산조직응용"],
        "건설업": ["건설업(토목공사)", "건설업(전기공사)", "종합건설업"],
        "감리법인": ["감리법인"],
        "ISMS": ["ISMS", "정보보호관리체계"],
        "ISO27001": ["ISO27001", "ISO/IEC 27001"],
        "CMMI": ["CMMI"],
        "기업부설연구소": ["기업부설연구소"],
        "연구개발전담요원": ["연구개발전담"],
        "물품등록": ["물품등록", "나라장터"],
        "직접생산": ["직접생산"],
        "제조사": ["제조사"],
    }

    for key, kia_keywords in license_map.items():
        if key in req:
            matched = [lic for lic in kia_licenses if any(kw in lic for kw in kia_keywords)]
            if matched:
                return QualificationMatch(
                    requirement=req,
                    status="충족",
                    evidence=f"보유 면허 매칭: {', '.join(matched)}",
                    kia_evidence=f"KIA 보유: {', '.join(matched)}",
                )
            # 기업부설연구소는 필수 요건인 경우가 많음
            if key in ("기업부설연구소", "연구개발전담요원"):
                return QualificationMatch(
                    requirement=req,
                    status="미충족",
                    evidence=f"필수 요건({key}) 미보유",
                    kia_evidence=f"KIA 미보유: {key}",
                )
            # 그 외는 확인불가로 넘김
            return QualificationMatch(
                requirement=req,
                status="확인불가",
                evidence=f"{key} 보유 여부 자동 판단 불가",
                kia_evidence="",
            )

    # 실적 관련 - 수치 비교 가능
    if "수행실적" in req and "건 이상" in req:
        import re
        m = re.search(r"(\d+)\s*건\s*이상", req)
        if m:
            required = int(m.group(1))
            # 카테고리 유추
            target_cat = _infer_category(req)
            if target_cat:
                relevant = [tr for tr in company.track_records if tr.category == target_cat]
                if len(relevant) >= required:
                    return QualificationMatch(
                        requirement=req,
                        status="충족",
                        evidence=f"{target_cat} 실적 {len(relevant)}건 보유 (≥{required}건)",
                        kia_evidence=", ".join([f"{tr.project_name}({tr.amount_display})" for tr in relevant[:required]]),
                    )
                elif len(relevant) > 0:
                    return QualificationMatch(
                        requirement=req,
                        status="부분충족",
                        evidence=f"{target_cat} 실적 {len(relevant)}건만 보유 (<{required}건)",
                        kia_evidence=", ".join([f"{tr.project_name}({tr.amount_display})" for tr in relevant]),
                    )

    # 예산 규모 비교
    if "예산" in req and "50%" in req:
        # 메타에서 예산 50% 이상 실적 확인 로직은 별도 처리
        pass

    return QualificationMatch(
        requirement=req,
        status="확인불가",
        evidence="규칙 기반 자동 판단 불가",
        kia_evidence="",
    )


def _infer_category(req: str) -> str | None:
    req_lower = req.lower()
    if any(kw in req_lower for kw in ["정보화", "CCTV", "플랫폼", "빅데이터", "블록체인", "민원", "모바일", "시스템"]):
        return "정보화사업"
    if any(kw in req_lower for kw in ["자율주행", "연구개발", "R&D", "인지판단", "레벨4", "양자", "반도체", "우주"]):
        return "연구개발사업"
    if any(kw in req_lower for kw in ["주차장", "청사", "리모델링", "그린리모델링", "온실", "스마트팜", "연구실험", "공사"]):
        return "시설공사"
    if any(kw in req_lower for kw in ["용역", "성능튜닝", "데이터품질", "자산관리", "DB", "데이터베이스", "컨설팅", "취약점"]):
        return "용역"
    if any(kw in req_lower for kw in ["노트북", "PC", "스토리지", "장비", "물품"]):
        return "물품구매"
    return None


async def _llm_match(
    requirement: str,
    company: CompanyProfile,
    llm_client: "AsyncOpenAI",
) -> QualificationMatch:
    """LLM을 통한 자격요건 판단"""
    from src.llm.prompts import build_qualification_prompt
    from src.data.models import QualificationMatch
    from src.config import get_settings

    prompt = build_qualification_prompt(requirement, company)

    response = await llm_client.beta.chat.completions.parse(
        model="openai/gpt-5.6-luna",
        messages=[{"role": "user", "content": prompt}],
        response_format=QualificationMatch,
        temperature=get_settings().llm_temperature,
    )
    return response.choices[0].message.parsed