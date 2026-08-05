"""리스크 분석 및 감점 계산"""

from src.data.models import BidRecord, RiskItem

SEVERITY_WEIGHTS = {
    "high": 0.30,
    "medium": 0.15,
    "low": 0.05,
}


def calculate_risk_penalty(record: BidRecord) -> float:
    """리스크 아이템 기반 감점 계산 (0~1 사이)"""
    if not record.risky_items:
        return 0.0

    total_penalty = 0.0
    for item in record.risky_items:
        severity = item.severity.lower() if isinstance(item.severity, str) else "low"
        weight = SEVERITY_WEIGHTS.get(severity, 0.05)
        total_penalty += weight

    # 최대 1.0으로 클램핑
    return min(1.0, total_penalty)


def get_key_risks(record: BidRecord) -> list[str]:
    """리포트용 핵심 리스크 문구 추출"""
    if not record.risky_items:
        return []

    risks = []
    for item in record.risky_items:
        severity = item.severity.upper() if isinstance(item.severity, str) else "LOW"
        risks.append(f"[{severity}] {item.risk}: {item.desc}")
    return risks