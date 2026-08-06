"""Tolerant field mapping for externally provided bid metadata.

The corpus ships as `bid_meta/*.json` whose exact key spelling varies by source
(나라장터 export, 지자체 홈페이지, 수작업 정리본). Every reader goes through these
alias tables so a renamed column degrades to a missing field, never a crash.
"""

import re
from datetime import date, datetime

from app.rag.parser import parse_krw

ALIASES: dict[str, tuple[str, ...]] = {
    "bid_id": ("공고번호", "bid_no", "bid_id", "notice_no", "announcement_id", "id"),
    "title": ("사업명", "공고명", "title", "name", "용역명", "과업명"),
    "agency": ("발주처", "발주기관", "수요기관", "agency", "organization", "org"),
    # `bid_date` is 나라장터's 입찰마감일. It is the submission cut-off, so it
    # ranks above open_date (개찰) — bidding closes before the box is opened.
    "deadline": (
        "마감일", "마감일시", "deadline", "due_date", "closing_date", "제출마감",
        "입찰마감", "bid_date",
    ),
    "announced": ("공고일자", "공고일", "announce_date", "announcement_date", "게시일"),
    "budget": ("예산", "사업예산", "budget", "estimated_price", "추정가격", "배정예산"),
    "region": ("지역", "사업지역", "region", "이행지역", "location"),
    "industry_code": ("업종코드", "industry_code", "업종", "license_code", "업종분류"),
    "duration": ("수행기간", "사업기간", "duration", "계약기간"),
    "duration_months": ("duration_months", "사업기간개월", "계약개월"),
    "category": ("사업분류", "category", "분류", "business_type", "공고종류"),
    "qualifications": ("qualifications", "자격요건", "입찰참가자격", "참가자격"),
    "eval_criteria": ("eval_criteria", "평가기준", "배점", "평가항목"),
    "risky_items": ("risky_items", "리스크", "위험요소", "특이사항"),
}

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y.%m.%d %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y%m%d",
)


def pick(meta: dict, field: str) -> object | None:
    """Return the first present alias for a logical field, case-insensitively."""
    lowered = {str(key).strip().lower(): value for key, value in meta.items()}
    for alias in ALIASES.get(field, ()):
        value = lowered.get(alias.lower())
        if value not in (None, "", [], {}):
            return value
    return None


def pick_str(meta: dict, field: str) -> str | None:
    value = pick(meta, field)
    return str(value).strip() or None if value is not None else None


def pick_list(meta: dict, field: str) -> list[str]:
    value = pick(meta, field)
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in re.split(r"[,/|]", str(value)) if part.strip()]


def pick_budget(meta: dict) -> int | None:
    value = pick(meta, "budget")
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    return parse_krw(str(value))


def pick_duration(meta: dict) -> str | None:
    """A human-readable 사업기간, from either a text field or a month count."""
    text = pick_str(meta, "duration")
    if text:
        return text
    months = pick(meta, "duration_months")
    if isinstance(months, (int, float)) and months > 0:
        return f"{int(months)}개월"
    return None


def pick_dict(meta: dict, field: str) -> dict:
    value = pick(meta, field)
    return value if isinstance(value, dict) else {}


def pick_dicts(meta: dict, field: str) -> list[dict]:
    value = pick(meta, field)
    if not isinstance(value, (list, tuple)):
        return []
    return [item for item in value if isinstance(item, dict)]


def parse_deadline(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    match = re.search(r"(\d{4})[-./년]\s*(\d{1,2})[-./월]\s*(\d{1,2})", text)
    if match:
        year, month, day = (int(group) for group in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None
