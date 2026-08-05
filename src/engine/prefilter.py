"""사전 필터 (결정론적) - 레퍼런스 filters.py 계승"""

from datetime import date
from src.data.models import BidRecord, CompanyProfile, PrefilterResult

# 지역제한 키워드
REGION_RESTRICTION_MARKERS = ("지역제한", "지역 제한", "본점 소재지", "소재지 제한", "지역우대")


def prefilter(record: BidRecord, company: CompanyProfile, today: date | None = None) -> PrefilterResult:
    """
    결정론적 사전 필터링:
    - 마감 경과, 예산 미달, 업종코드 미보유, 지역제한 불일치 -> 차단(blocked=True)
    - 마감 임박(D-7 이내) -> urgent 플래그만 (차단 안 함)
    """
    today = today or date.today()
    result = PrefilterResult()

    # 1. 마감일 체크
    if record.deadline:
        result.days_left = (record.deadline - today).days
        if result.days_left < 0:
            result.blocked = True
            result.reasons.append(f"마감경과 (마감 {record.deadline}, {-result.days_left}일 지남)")
        elif result.days_left < company.min_preparation_days if hasattr(company, 'min_preparation_days') else 7:
            result.urgent = True
            result.warnings.append(f"마감임박 (D-{result.days_left})")
    else:
        result.warnings.append("마감일 확인 불가")

    # 2. 예산 체크 (최소 수주 기준 10억)
    if record.budget < company.min_project_amount:
        result.blocked = True
        result.reasons.append(
            f"예산미달 ({_krw(record.budget)} < 최소 수주 기준 {_krw(company.min_project_amount)})"
        )

    # 3. 업종코드/면허 체크
    # 실제 데이터에 industry_code가 없으므로, 카테고리별 필요 면허 매핑으로 대체
    required_licenses = _get_required_licenses_for_category(record.category)
    if required_licenses:
        has_license = any(any(req in lic for lic in company.licenses) for req in required_licenses)
        if not has_license:
            result.blocked = True
            result.reasons.append(f"자격미달 (필요 면허: {', '.join(required_licenses)} 미보유)")

    # 4. 지역제한 체크
    if _is_region_restricted(record.markdown, record.region) and company.preferred_regions:
        if not any(region in (record.region or "") for region in company.preferred_regions):
            result.blocked = True
            result.reasons.append(f"자격미달 (지역제한 {record.region}, 영업권역 불일치)")

    return result


def _get_required_licenses_for_category(category: str) -> list[str]:
    """카테고리별 필수 면허 키워드 매핑"""
    mapping = {
        "정보화사업": ["소프트웨어사업", "정보처리", "전자계산", "정보통신공사"],
        "연구개발사업": ["기업부설연구소", "연구개발전담"],
        "시설공사": ["건설업", "종합건설", "토목", "건축", "전기공사"],
        "용역": ["소프트웨어사업", "정보처리", "정보보호"],
        "물품구매": ["물품등록", "제조", "공급", "직접생산"],
    }
    return mapping.get(category, [])


def _is_region_restricted(markdown: str, region: str | None) -> bool:
    haystack = f"{markdown}\n{region or ''}"
    return any(marker in haystack for marker in REGION_RESTRICTION_MARKERS)


def _krw(amount: int | None) -> str:
    if not amount:
        return "미확인"
    if amount >= 10**8:
        return f"{amount / 10**8:.1f}억원"
    if amount >= 10**4:
        return f"{amount / 10**4:.0f}만원"
    return f"{amount:,}원"