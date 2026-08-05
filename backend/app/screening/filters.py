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
