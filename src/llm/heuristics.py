"""오프라인 휴리스틱 폴백 - API 키 없을 때/호출 실패 시 사용"""

from src.data.models import BidRecord, CompanyProfile, QualificationMatch

# 자격요건 키워드 매칭용
LICENSE_KEYWORDS = {
    "소프트웨어사업": ["소프트웨어사업", "일반소프트웨어", "정보처리시스템"],
    "정보통신공사": ["정보통신공사"],
    "전자계산": ["전자계산", "전자계산조직"],
    "건설업": ["건설업", "토목", "건축", "전기공사"],
    "정보보호": ["정보보호", "ISMS", "ISO27001"],
    "감리법인": ["감리법인"],
    "기업부설연구소": ["기업부설연구소", "연구소"],
    "연구개발전담": ["연구개발전담", "전담요원"],
    "물품등록": ["물품등록", "나라장터", "조달등록"],
    "제조": ["제조", "직접생산", "공급"],
}

TRACK_RECORD_KEYWORDS = {
    "정보화사업": ["정보화", "플랫폼", "시스템", "CCTV", "빅데이터", "블록체인", "민원", "모바일"],
    "연구개발사업": ["자율주행", "연구개발", "R&D", "인지판단", "레벨4"],
    "시설공사": ["주차장", "청사", "리모델링", "그린리모델링", "온실", "스마트팜", "연구실험"],
    "용역": ["용역", "성능튜닝", "데이터품질", "자산관리", "DB", "데이터베이스"],
    "물품구매": ["노트북", "PC", "스토리지", "하드웨어", "장비"],
}


def heuristic_qualification_match(
    record: BidRecord, company: CompanyProfile
) -> list[QualificationMatch]:
    """규칙 기반 자격요건 매칭 (LLM 폴백)"""
    results = []

    # KIA 보유 자격 요약
    kia_licenses = set(company.licenses)
    kia_cats = set(tr.category for tr in company.track_records)

    for req in record.qualifications:
        status, evidence, kia_evidence = _match_single_requirement(req, company, kia_licenses, kia_cats)
        results.append(QualificationMatch(
            requirement=req,
            status=status,
            evidence=evidence,
            kia_evidence=kia_evidence,
        ))

    return results


def _match_single_requirement(
    req: str, company: CompanyProfile, kia_licenses: set, kia_cats: set
) -> tuple[str, str, str]:
    req_lower = req.lower()

    # 1. 면허/인증 보유 확인
    for cat, keywords in LICENSE_KEYWORDS.items():
        if any(kw in req for kw in keywords):
            matched = [lic for lic in kia_licenses if any(kw in lic for kw in keywords)]
            if matched:
                return "충족", f"보유 면허 매칭: {', '.join(matched)}", f"KIA 보유: {', '.join(matched)}"
            else:
                return "미충족", f"필요 면허({cat}) 미보유", f"KIA 미보유: {cat}"

    # 2. 실적 건수/규모 확인
    if "수행실적" in req or "수행 실적" in req or "유사 규모" in req:
        target_cat = _infer_category_from_req(req)
        if target_cat:
            relevant = [tr for tr in company.track_records if tr.category == target_cat]
            if len(relevant) >= 2:
                return "충족", f"{target_cat} 실적 {len(relevant)}건 보유", f"KIA {target_cat} 실적: {', '.join([tr.project_name for tr in relevant[:3]])}"
            elif len(relevant) == 1:
                return "부분충족", f"{target_cat} 실적 1건만 보유 (2건 필요)", f"KIA {target_cat} 실적: {relevant[0].project_name}"
            else:
                return "미충족", f"{target_cat} 실적 없음", f"KIA {target_cat} 실적 없음"

    # 3. 전문인력 확인
    if "전문인력" in req or "전담요원" in req or "기사" in req:
        if company.technical_staff and company.technical_staff.count >= 5:
            return "충족", f"기술인력 {company.technical_staff.count}명 보유", f"KIA 기술인력: {company.technical_staff.count}명 (고급 {company.technical_staff.senior_above}명)"
        return "미충족", "전문인력 부족", "KIA 인력 정보 없음"

    # 4. 감리법인/ISMS 등 특정 인증
    if "감리법인" in req:
        if any("감리" in lic for lic in kia_licenses):
            return "충족", "감리법인 등록 확인", "KIA 감리법인 보유"
        return "미충족", "감리법인 미등록", "KIA 감리법인 미보유"

    if "ISMS" in req or "정보보호관리체계" in req:
        if any("ISMS" in lic or "정보보호관리" in lic for lic in kia_licenses):
            return "충족", "ISMS 인증 보유", "KIA ISMS 인증 보유"
        return "미충족", "ISMS 인증 미보유", "KIA ISMS 인증 미보유"

    # 5. 중소기업/공동도급 등 조건부
    if "중소기업" in req:
        return "부분충족", "중소기업 해당 여부 확인 필요 (KIA는 대기업)", "KIA: 대기업 (중소기업 아님)"

    if "공동도급" in req or "공동수급" in req:
        return "충족", "공동도급 가능 (주관사 자격 충족 시)", "KIA 주관사 역량 보유"

    # 기본: 확인불가
    return "확인불가", "자동 판단 불가, 수동 검토 필요", ""


def _infer_category_from_req(req: str) -> str | None:
    req_lower = req.lower()
    for cat, keywords in TRACK_RECORD_KEYWORDS.items():
        if any(kw in req_lower for kw in keywords):
            return cat
    return None