"""스코어링 엔진 - 가중치 합산 방식"""

from dataclasses import dataclass

from src.data.models import BidRecord, CompanyProfile, PrefilterResult, QualificationMatch, ScoreBreakdown
from src.engine.risk import calculate_risk_penalty

# 가중치 설정
WEIGHTS = {
    "qualification_fit": 0.35,
    "budget_fit": 0.20,
    "track_record_match": 0.20,
    "eval_criteria_advantage": 0.15,
    "risk_penalty": -0.10,
}

# 등급 임계값
STRONG_THRESHOLD = 0.75
REVIEW_THRESHOLD = 0.50


@dataclass
class ScoreComponents:
    qualification_fit: float
    budget_fit: float
    track_record_match: float
    eval_criteria_advantage: float
    risk_penalty: float


def calculate_score(
    record: BidRecord,
    company: CompanyProfile,
    qual_matches: list[QualificationMatch],
    prefilter: PrefilterResult,
) -> tuple[float, ScoreBreakdown, str]:
    """
    종합 스코어 계산
    Returns: (total_score, breakdown, reason)
    """

    # 1. 자격적합도 (0~1)
    qual_fit = _calc_qualification_fit(qual_matches)

    # 2. 예산적정성 (0~1)
    budget_fit = _calc_budget_fit(record.budget, company)

    # 3. 실적매칭도 (0~1)
    track_match = _calc_track_record_match(record, company)

    # 4. 평가기준 유리도 (0~1)
    eval_adv = _calc_eval_criteria_advantage(record)

    # 5. 리스크 감점 (0~1, 음수)
    risk_penalty = calculate_risk_penalty(record)

    # 가중 합산
    total = (
        WEIGHTS["qualification_fit"] * qual_fit
        + WEIGHTS["budget_fit"] * budget_fit
        + WEIGHTS["track_record_match"] * track_match
        + WEIGHTS["eval_criteria_advantage"] * eval_adv
        + WEIGHTS["risk_penalty"] * risk_penalty
    )

    # 0~1 클램핑
    total = max(0.0, min(1.0, total))

    breakdown = ScoreBreakdown(
        qualification_fit=round(qual_fit, 3),
        budget_fit=round(budget_fit, 3),
        track_record_match=round(track_match, 3),
        eval_criteria_advantage=round(eval_adv, 3),
        risk_penalty=round(risk_penalty, 3),
    )

    # 등급 결정
    if total >= STRONG_THRESHOLD:
        grade = "적극추천"
    elif total >= REVIEW_THRESHOLD:
        grade = "검토"
    else:
        grade = "패스"

    # 핵심 사유 생성
    reason = _build_reason(grade, qual_fit, budget_fit, track_match, eval_adv, risk_penalty, prefilter)

    return total, breakdown, reason


def _calc_qualification_fit(matches: list[QualificationMatch]) -> float:
    """자격적합도: 필수요건 충족률. 미충족 1개면 큰 감점"""
    if not matches:
        return 0.0

    # 필수/조건부 구분 (해당시, 공동도급시 등은 조건부)
    mandatory = [m for m in matches if "해당시" not in m.requirement and "공동도급" not in m.requirement and "중소기업" not in m.requirement]

    if not mandatory:
        return 1.0

    status_weights = {"충족": 1.0, "부분충족": 0.5, "확인불가": 0.3, "미충족": 0.0}
    scores = [status_weights.get(m.status, 0.0) for m in mandatory]

    # 미충족이 있으면 전체 점수 대폭 감점
    if any(m.status == "미충족" for m in mandatory):
        return sum(scores) / len(scores) * 0.3

    return sum(scores) / len(scores)


def _calc_budget_fit(budget: int, company: CompanyProfile) -> float:
    """예산적정성: 최소금액~적정상한 사이면 1.0, 벗어나면 선형 감점"""
    min_amt = company.min_project_amount
    # 상한: KIA 최대 수행 실적의 2배 정도 (또는 연매출 추정치의 10%)
    max_amt = max(tr.amount for tr in company.track_records) * 2 if company.track_records else 500_000_000_000

    if budget < min_amt:
        return max(0.0, budget / min_amt * 0.5)
    if budget > max_amt:
        return max(0.3, max_amt / budget)
    return 1.0


def _calc_track_record_match(record: BidRecord, company: CompanyProfile) -> float:
    """유사실적 매칭도: 동일 카테고리, 유사 규모 실적 보유 비율"""
    target_cat = record.category
    relevant = [tr for tr in company.track_records if tr.category == target_cat]

    if not relevant:
        # 관련 카테고리 실적 없음
        return 0.1

    # 규모 적정성: 예산의 50% 이상 실적이 몇 건인가
    budget_half = record.budget * 0.5
    large_enough = [tr for tr in relevant if tr.amount >= budget_half]

    # 기본 점수: 관련 실적 있으면 0.5, 규모 충족하면 추가
    base = 0.5
    scale_bonus = min(0.5, len(large_enough) / 3 * 0.5)
    return min(1.0, base + scale_bonus)


def _calc_eval_criteria_advantage(record: BidRecord) -> float:
    """평가기준 유리도: 기술능력 배점이 높을수록 KIA에 유리"""
    criteria = record.eval_criteria
    if not criteria:
        return 0.5

    tech = criteria.get("기술능력", criteria.get("기술", 0))
    price = criteria.get("가격", criteria.get("가격점수", 0))
    total_tech_price = tech + price

    if total_tech_price == 0:
        return 0.5

    tech_ratio = tech / total_tech_price
    # 기술비중 60% 이상이면 1.0, 40% 미만이면 0.3
    if tech_ratio >= 0.6:
        return 1.0
    elif tech_ratio >= 0.4:
        return 0.7
    else:
        return 0.3


def _build_reason(
    grade: str,
    qual_fit: float,
    budget_fit: float,
    track_match: float,
    eval_adv: float,
    risk_penalty: float,
    prefilter: PrefilterResult,
) -> str:
    parts = []

    if prefilter.urgent:
        parts.append(f"D-{prefilter.days_left} 마감임박")

    if grade == "적극추천":
        if qual_fit >= 0.8:
            parts.append("자격요건 완전 충족")
        if budget_fit >= 0.8:
            parts.append("예산 규모 적정")
        if track_match >= 0.7:
            parts.append("유사 실적 다수 보유")
        if eval_adv >= 0.8:
            parts.append("기술 중심 평가 유리")
    elif grade == "검토":
        if qual_fit < 0.7:
            parts.append("일부 자격요건 미충족/확인필요")
        if budget_fit < 0.7:
            parts.append("예산 규모 확인 필요")
        if track_match < 0.5:
            parts.append("유사 실적 부족")
    else:
        parts.append("자격미달 또는 예산미달")

    if risk_penalty > 0.2:
        parts.append("고위험 요소 존재")

    return " · ".join(parts) if parts else "종합 평가"