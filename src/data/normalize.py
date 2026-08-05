"""메타데이터 키 관용 매핑 - 레퍼런스 normalize.py 계승"""

import re
from datetime import date, datetime
from typing import Any

KRW_UNITS = {"조": 10**12, "억": 10**8, "만": 10**4}

ALIASES: dict[str, tuple[str, ...]] = {
    "bid_id": ("공고번호", "bid_no", "bid_id", "notice_no", "announcement_id", "id"),
    "title": ("사업명", "공고명", "title", "name", "용역명", "과업명"),
    "agency": ("발주처", "발주기관", "수요기관", "공고기관", "agency", "organization", "org"),
    "deadline": ("마감일", "마감일시", "deadline", "due_date", "closing_date", "제출마감", "bid_date", "입찰마감"),
    "budget": ("예산", "사업예산", "budget", "estimated_price", "추정가격", "배정예산"),
    "region": ("지역", "사업지역", "region", "이행지역", "소재지"),
    "industry_code": ("업종코드", "industry_code", "업종", "license_code", "업종분류"),
    "duration": ("수행기간", "사업기간", "duration", "계약기간", "duration_months"),
    "category": ("사업분류", "category", "공고구분", "용역구분"),
    "qualifications": ("자격요건", "입찰참가자격", "qualifications", "참가자격"),
    "eval_criteria": ("평가기준", "배점", "eval_criteria", "evaluation_criteria", "심사기준"),
    "risky_items": ("리스크", "위험요소", "risky_items", "특이사항"),
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


def pick(meta: dict, field: str) -> Any | None:
    """첫 번째로 존재하는 별칭 값 반환 (대소문자 무시)"""
    lowered = {str(k).strip().lower(): v for k, v in meta.items()}
    for alias in ALIASES.get(field, ()):
        v = lowered.get(alias.lower())
        if v not in (None, "", [], {}):
            return v
    return None


def pick_str(meta: dict, field: str) -> str | None:
    v = pick(meta, field)
    return str(v).strip() if v is not None else None


def pick_list(meta: dict, field: str) -> list[str]:
    v = pick(meta, field)
    if v is None:
        return []
    if isinstance(v, (list, tuple, set)):
        return [str(x).strip() for x in v if str(x).strip()]
    # 문자열이면 구분자로 분할
    return [part.strip() for part in re.split(r"[,/|]", str(v)) if part.strip()]


def pick_budget(meta: dict) -> int | None:
    v = pick(meta, "budget")
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    return parse_krw(str(v))


def parse_deadline(value: Any) -> date | None:
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
    # 한국어 날짜 패턴: 2025-08-17, 2025.08.17, 2025년 8월 17일 등
    m = re.search(r"(\d{4})[-./년]\s*(\d{1,2})[-./월]\s*(\d{1,2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def parse_krw(text: str) -> int | None:
    """'28.0억', '2,803,000,000원', '2803000000' 등 파싱"""
    if not text:
        return None
    compact = text.replace(",", "").replace(" ", "")
    # 단위(조/억/만) 있는 경우
    unit_matches = list(re.finditer(r"(\d+(?:\.\d+)?)(조|억|만)", compact))
    if unit_matches:
        total = 0.0
        for m in unit_matches:
            total += float(m.group(1)) * KRW_UNITS[m.group(2)]
        # 나머지 원 단위
        tail = re.search(r"[조억만](\d+)원", compact)
        if tail:
            total += float(tail.group(1))
        return round(total)
    # 순수 숫자+원
    plain = re.search(r"(\d{5,})원", compact)
    if plain:
        return int(plain.group(1))
    # 숫자만 있는 경우
    if compact.isdigit():
        return int(compact)
    return None


def parse_duration_months(value: Any) -> int | None:
    """'20개월', '2년', '57개월' -> 개월 수"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    m = re.search(r"(\d+)\s*(?:개월|달)", text)
    if m:
        return int(m.group(1))
    y = re.search(r"(\d+)\s*년", text)
    if y:
        return int(y.group(1)) * 12
    d = re.search(r"(\d+)\s*일", text)
    if d:
        return max(1, int(d.group(1)) // 30)
    # 숫자만 있으면 개월로 가정
    if text.isdigit():
        return int(text)
    return None