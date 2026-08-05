"""코퍼스 로드: bids_md/ + bid_meta/ + company_profile.json"""

import json
import logging
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.data.models import BidRecord, CompanyProfile, RiskItem, TrackRecord, TechnicalStaff
from src.data.normalize import (
    parse_deadline,
    parse_duration_months,
    pick,
    pick_budget,
    pick_list,
    pick_str,
)

logger = logging.getLogger(__name__)

MARKDOWN_DIRS = ("bids_md", "bids")
META_DIR = "bid_meta"
COMPANY_FILE = "company_profile.json"


def load_corpus(root: Path | None = None) -> list[BidRecord]:
    settings = get_settings()
    root = root or settings.corpus_path

    documents = _load_documents(root)
    meta = _load_meta(root)

    records = []
    for bid_id, (markdown, source) in sorted(documents.items()):
        m = meta.get(bid_id, {})
        record = _build_record(bid_id, markdown, m, source)
        if record:
            records.append(record)

    matched = {r.bid_id for r in records if r.bid_id in meta}
    unmatched = [r.bid_id for r in records if r.bid_id not in meta]
    if unmatched:
        logger.warning("메타데이터 없는 문서: %s", unmatched)
    logger.info("로드 완료: %d건 (메타 매칭 %d건)", len(records), len(matched))
    return records


def _load_documents(root: Path) -> dict[str, tuple[str, str]]:
    docs: dict[str, tuple[str, str]] = {}
    for dir_name in MARKDOWN_DIRS:
        d = root / dir_name
        if not d.is_dir():
            continue
        for path in sorted(d.iterdir()):
            if path.suffix.lower() not in {".md", ".markdown", ".txt", ".pdf"}:
                continue
            # bids_md 우선 (이미 변환된 것)
            if path.stem in docs:
                continue
            try:
                text = path.read_text(encoding="utf-8")
                docs[path.stem] = (text, str(path.name))
            except Exception:
                logger.exception("문서 읽기 실패: %s", path)
    return docs


def _load_meta(root: Path) -> dict[str, dict]:
    meta_dir = root / META_DIR
    if not meta_dir.is_dir():
        return {}
    meta: dict[str, dict] = {}
    for path in sorted(meta_dir.glob("*.json")):
        if path.name == COMPANY_FILE:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.exception("JSON 파싱 실패: %s", path)
            continue
        for keys, entry in _iter_entries(payload, path.stem):
            for key in keys:
                meta.setdefault(key, entry)
    return meta


def _iter_entries(payload: Any, stem: str) -> list[tuple[list[str], dict]]:
    """단일 객체, 리스트, 키-값 객체 모두 처리"""
    if isinstance(payload, dict):
        vals = list(payload.values())
        if vals and all(isinstance(v, dict) for v in vals):
            return [
                ([str(k), *_alias_keys(v)], v)
                for k, v in payload.items()
                if isinstance(v, dict)
            ]
        return [([stem, *_alias_keys(payload)], payload)]
    if isinstance(payload, list):
        return [
            ([f"{stem}-{i}", *_alias_keys(e)], e)
            for i, e in enumerate(payload)
            if isinstance(e, dict)
        ]
    return []


def _alias_keys(entry: dict) -> list[str]:
    bid_id = pick_str(entry, "bid_id")
    return [bid_id] if bid_id else []


def _build_record(bid_id: str, markdown: str, meta: dict, source: str) -> BidRecord | None:
    try:
        # 메타에서 기본 필드 추출
        title = pick_str(meta, "title") or bid_id
        category = pick_str(meta, "category") or "미분류"
        agency = pick_str(meta, "agency") or "미상"
        budget = pick_budget(meta) or 0
        deadline = parse_deadline(pick(meta, "deadline"))
        duration = parse_duration_months(pick(meta, "duration"))
        region = pick_str(meta, "region")
        qualifications = pick_list(meta, "qualifications")
        eval_criteria = _parse_eval_criteria(meta)
        risky_items = _parse_risky_items(meta)

        if not deadline:
            logger.warning("마감일 파싱 실패: %s (meta: %s)", bid_id, pick(meta, "deadline"))

        return BidRecord(
            bid_id=bid_id,
            title=title,
            category=category,
            agency=agency,
            budget=budget,
            deadline=deadline,
            duration_months=duration or 0,
            region=region,
            qualifications=qualifications,
            eval_criteria=eval_criteria,
            risky_items=risky_items,
            markdown=markdown,
        )
    except Exception:
        logger.exception("레코드 생성 실패: %s", bid_id)
        return None


def _parse_eval_criteria(meta: dict) -> dict[str, int]:
    raw = pick(meta, "eval_criteria")
    if not raw:
        return {}
    if isinstance(raw, dict):
        return {str(k): int(v) for k, v in raw.items() if isinstance(v, (int, float, str))}
    # 문자열인 경우 파싱 시도
    text = str(raw)
    result = {}
    for line in text.split("\n"):
        for sep in [":", "：", "="]:
            if sep in line:
                k, v = line.split(sep, 1)
                k = k.strip()
                m = re.search(r"(\d+)", v)
                if m:
                    result[k] = int(m.group(1))
                break
    return result


def _parse_risky_items(meta: dict) -> list[RiskItem]:
    raw = pick(meta, "risky_items")
    if not raw:
        return []
    if isinstance(raw, list):
        items = []
        for r in raw:
            if isinstance(r, dict):
                items.append(
                    RiskItem(
                        item=str(r.get("item", "")),
                        risk=str(r.get("risk", "")),
                        severity=str(r.get("severity", "low")),
                        desc=str(r.get("desc", "")),
                    )
                )
        return items
    return []


def load_company(root: Path | None = None) -> CompanyProfile:
    settings = get_settings()
    root = root or settings.corpus_path

    for candidate in (root / META_DIR / COMPANY_FILE, root / COMPANY_FILE):
        if candidate.is_file():
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
                return _to_company(payload)
            except Exception:
                logger.exception("회사 프로필 로드 실패: %s", candidate)
    # 폴백
    return CompanyProfile(name="KIA")


def _to_company(payload: dict) -> CompanyProfile:
    # 라이선스/인증 - 객체 리스트에서 name 추출
    raw_licenses = payload.get("licenses", [])
    if isinstance(raw_licenses, list) and raw_licenses and isinstance(raw_licenses[0], dict):
        licenses = [str(item.get("name", "")) for item in raw_licenses if item.get("name")]
    else:
        licenses = pick_list(payload, "licenses") or _listify(raw_licenses)

    certifications = pick_list(payload, "certifications") or _listify(payload.get("certifications"))

    # 실적
    track_records = []
    for tr in _listify(payload.get("track_records")):
        if isinstance(tr, dict):
            track_records.append(
                TrackRecord(
                    project_name=str(tr.get("project_name", tr.get("title", ""))),
                    year=int(tr.get("year", 0)),
                    amount=int(tr.get("amount", 0)),
                    client=str(tr.get("client", tr.get("agency", ""))),
                    category=str(tr.get("category", "")),
                )
            )

    # 기술인력
    tech_staff = None
    ts = payload.get("technical_staff")
    if isinstance(ts, dict):
        tech_staff = TechnicalStaff(
            count=int(ts.get("count", 0)),
            breakdown={k: int(v) for k, v in ts.get("breakdown", {}).items()},
            senior_above=int(ts.get("senior_above", 0)),
        )

    # 자본금 - 콤마 제거
    capital_raw = payload.get("capital", 0)
    if isinstance(capital_raw, str):
        capital = int(capital_raw.replace(",", "")) or None
    else:
        capital = int(capital_raw) if capital_raw else None

    return CompanyProfile(
        name=str(payload.get("company_name", payload.get("name", "KIA"))),
        stock_code=str(payload.get("stock_code", "")) or None,
        business_type=str(payload.get("business_type", "")) or None,
        capital=capital,
        established=str(payload.get("established", "")) or None,
        employees=int(payload.get("employees", 0)) or None,
        licenses=licenses,
        certifications=certifications,
        track_records=track_records,
        technical_staff=tech_staff,
        preferred_regions=pick_list(payload, "regions") or _listify(payload.get("regions")),
        target_categories=pick_list(payload, "preferred_categories")
        or _listify(payload.get("preferred_categories")),
        min_project_amount=int(payload.get("min_project_amount", 1_000_000_000)),
    )


def _listify(v: Any) -> list:
    if v is None:
        return []
    if isinstance(v, (list, tuple, set)):
        return list(v)
    return [v]