"""Deterministic prefilters.

These run before any agent so obviously ineligible notices never cost an LLM
call. Only unambiguous, checkable facts block a bid; anything requiring judgement
is left to the committee.
"""

from datetime import date

from app.schemas import CompanyProfile, ScreenOutcome
from app.screening import normalize
from app.screening.dataset import BidRecord

REGION_RESTRICTION_MARKERS = ("지역제한", "지역 제한", "본점 소재지", "소재지 제한")


def prefilter(
    record: BidRecord,
    company: CompanyProfile,
    today: date | None = None,
) -> ScreenOutcome:
    today = today or date.today()
    facts = record.facts()
    outcome = ScreenOutcome()

    deadline = normalize.parse_deadline(
        normalize.pick(record.meta, "deadline") or facts.deadline
    )
    if deadline:
        outcome.days_left = (deadline - today).days
        if outcome.days_left < 0:
            outcome.blocked = True
            outcome.block_reasons.append(f"마감경과 (마감 {deadline}, {-outcome.days_left}일 지남)")
        elif outcome.days_left < company.min_preparation_days:
            outcome.urgent = True
            outcome.warnings.append(
                f"마감임박 (D-{outcome.days_left}, 최소 준비기간 {company.min_preparation_days}일 미만)"
            )
    else:
        outcome.warnings.append("마감일을 확인하지 못함")

    if facts.budget_krw is None:
        outcome.warnings.append("예산을 확인하지 못함")
    elif company.min_project_budget_krw and facts.budget_krw < company.min_project_budget_krw:
        outcome.blocked = True
        outcome.block_reasons.append(
            f"예산미달 ({_krw(facts.budget_krw)} < 최소 수주 기준 {_krw(company.min_project_budget_krw)})"
        )

    # 주력 분야 여부는 판단의 영역이라 차단하지 않고 위원회로 넘긴다.
    category = record.category
    if category and company.preferred_categories and category not in company.preferred_categories:
        outcome.warnings.append(
            f"비주력 분야 ({category}, 주력: {', '.join(company.preferred_categories)})"
        )

    # 코퍼스가 이미 식별해 둔 리스크는 다시 추론하지 않고 그대로 승계한다.
    for item in record.risky_items:
        if str(item.get("severity", "")).lower() == "high":
            label = item.get("risk") or item.get("item") or "고위험 항목"
            detail = str(item.get("desc") or "").strip()
            outcome.warnings.append(f"{label}{f' — {detail}' if detail else ''}")

    required_codes = normalize.pick_list(record.meta, "industry_code")
    if required_codes and company.industry_codes:
        if not set(required_codes) & set(company.industry_codes):
            outcome.blocked = True
            outcome.block_reasons.append(
                f"자격미달 (요구 업종코드 {', '.join(required_codes)} 미보유)"
            )

    if _region_restricted(record.markdown, facts.region) and company.regions:
        if not any(region in (facts.region or "") for region in company.regions):
            outcome.blocked = True
            outcome.block_reasons.append(f"자격미달 (지역제한 {facts.region}, 소재지 불일치)")

    return outcome


def _region_restricted(markdown: str, region: str | None) -> bool:
    haystack = f"{markdown}\n{region or ''}"
    return any(marker in haystack for marker in REGION_RESTRICTION_MARKERS)


def _krw(amount: int | None) -> str:
    if not amount:
        return "미확인"
    if amount >= 10**8:
        return f"{amount / 10**8:.1f}억원"
    return f"{amount / 10**4:.0f}만원"
