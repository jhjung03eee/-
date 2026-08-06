"""Loads the `projects/raw` corpus layout: bids/, bids_md/, bid_meta/."""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from app.rag.parser import extract_facts, to_markdown
from app.schemas import BidFacts, CompanyProfile
from app.screening import normalize

logger = logging.getLogger(__name__)

MARKDOWN_DIRS = ("bids_md", "bids")
META_DIR = "bid_meta"
COMPANY_FILE = "company_profile.json"


@dataclass
class BidRecord:
    bid_id: str
    markdown: str
    meta: dict = field(default_factory=dict)
    source: str = ""

    def facts(self) -> BidFacts:
        """Document-derived facts, overridden by metadata where it is present.

        Metadata wins because it is curated; regex parsing only fills the gaps.
        """
        facts = extract_facts(self.markdown)
        overrides = {
            "title": normalize.pick_str(self.meta, "title"),
            "agency": normalize.pick_str(self.meta, "agency"),
            "deadline": normalize.pick_str(self.meta, "deadline"),
            "region": normalize.pick_str(self.meta, "region"),
            "duration": normalize.pick_duration(self.meta),
        }
        for key, value in overrides.items():
            if value:
                setattr(facts, key, value)

        budget = normalize.pick_budget(self.meta)
        if budget:
            facts.budget_krw = budget

        qualifications = normalize.pick_list(self.meta, "qualifications")
        if qualifications:
            facts.qualifications = qualifications

        # 배점표는 {"기술능력": 50, ...} 형태라 본문 불릿 파싱으로는 잡히지 않는다.
        criteria = normalize.pick_dict(self.meta, "eval_criteria")
        if criteria:
            facts.evaluation_criteria = [f"{name} {score}점" for name, score in criteria.items()]
        return facts

    @property
    def category(self) -> str | None:
        return normalize.pick_str(self.meta, "category")

    @property
    def risky_items(self) -> list[dict]:
        return normalize.pick_dicts(self.meta, "risky_items")

    @property
    def announced_on(self) -> date | None:
        return normalize.parse_deadline(normalize.pick(self.meta, "announced"))


def load_corpus(root: Path) -> list[BidRecord]:
    documents = _load_documents(root)
    meta = _load_meta(root)

    records = [
        BidRecord(bid_id=bid_id, markdown=markdown, meta=meta.get(bid_id, {}), source=source)
        for bid_id, (markdown, source) in sorted(documents.items())
    ]

    matched = {record.bid_id for record in records if record.meta}
    unmatched = [record.bid_id for record in records if not record.meta]
    if unmatched:
        logger.warning("documents without metadata: %s", unmatched)
    logger.info("loaded %d bids, %d with metadata", len(records), len(matched))
    return records


def corpus_as_of(records: list[BidRecord]) -> date | None:
    """The last day every notice in the corpus is simultaneously open.

    Archived corpora carry announcement dates in the past, so judging their
    deadlines against the wall clock rejects all of them as expired. Screening
    as of the newest announcement reproduces the moment a bid desk would
    actually have looked at this batch: everything published, nothing closed.
    """
    announced = [record.announced_on for record in records]
    return max((day for day in announced if day), default=None)


def load_company(root: Path) -> CompanyProfile | None:
    for candidate in (root / META_DIR / COMPANY_FILE, root / COMPANY_FILE):
        if candidate.is_file():
            return _to_company(json.loads(candidate.read_text(encoding="utf-8")))
    return None


def _load_documents(root: Path) -> dict[str, tuple[str, str]]:
    documents: dict[str, tuple[str, str]] = {}
    for directory in MARKDOWN_DIRS:
        source_dir = root / directory
        if not source_dir.is_dir():
            continue
        for path in sorted(source_dir.iterdir()):
            if path.suffix.lower() not in {".md", ".markdown", ".txt", ".pdf"}:
                continue
            # bids_md/ is read first; never let a PDF overwrite its converted twin.
            if path.stem in documents:
                continue
            try:
                payload = path.read_bytes()
                documents[path.stem] = (to_markdown(payload, path.name), str(path.name))
            except Exception:
                logger.exception("failed to read %s", path)
    return documents


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
            logger.exception("invalid JSON in %s", path)
            continue
        for keys, entry in _iter_entries(payload, path.stem):
            # Registered under every plausible join key: the document filename and
            # the 공고번호 inside the record. Whichever the documents use, we match.
            for key in keys:
                meta.setdefault(key, entry)
    return meta


def _iter_entries(payload: object, stem: str) -> list[tuple[list[str], dict]]:
    """Accept one-file-per-bid, a list of bids, or an object keyed by bid id."""
    if isinstance(payload, dict):
        values = list(payload.values())
        if values and all(isinstance(value, dict) for value in values):
            return [
                ([str(key), *_alias_keys(entry)], entry)
                for key, entry in payload.items()
                if isinstance(entry, dict)
            ]
        return [([stem, *_alias_keys(payload)], payload)]
    if isinstance(payload, list):
        return [
            ([f"{stem}-{index}", *_alias_keys(entry)], entry)
            for index, entry in enumerate(payload)
            if isinstance(entry, dict)
        ]
    return []


def _alias_keys(entry: dict) -> list[str]:
    bid_id = normalize.pick_str(entry, "bid_id")
    return [bid_id] if bid_id else []


def _to_company(payload: dict) -> CompanyProfile:
    """Map an arbitrary company profile onto our schema, keeping unknown keys out."""
    if "annual_revenue_krw" in payload and "name" in payload:
        return CompanyProfile(**{k: v for k, v in payload.items() if k in CompanyProfile.model_fields})

    business_type = _first_str(payload, "business_type", "업종", "사업분야")
    staff = payload.get("technical_staff") if isinstance(payload.get("technical_staff"), dict) else {}

    return CompanyProfile(
        name=_first_str(payload, "name", "company_name", "회사명", "company") or "당사",
        headcount=_first_int(payload, "headcount", "employees", "인력", "임직원수"),
        annual_revenue_krw=_first_int(payload, "annual_revenue_krw", "annual_revenue", "매출액"),
        capital_krw=_first_int(payload, "capital_krw", "capital", "자본금"),
        technical_headcount=_first_int(staff, "count", "technical_staff_count"),
        business_type=business_type,
        regions=normalize.pick_list(payload, "region") or _listify(payload.get("regions")),
        # 면허·인증은 이름만 뽑아 자격요건 문자열 매칭에 쓴다.
        certifications=_names(
            payload.get("licenses") or payload.get("certifications") or payload.get("인증"), "name"
        ),
        industry_codes=normalize.pick_list(payload, "industry_code"),
        tech_stack=_tech_stack(payload, business_type),
        past_projects=_names(
            payload.get("track_records") or payload.get("past_projects") or payload.get("실적"),
            "project_name",
        ),
        preferred_categories=_listify(payload.get("preferred_categories")),
        min_project_budget_krw=_first_int(
            payload, "min_project_budget_krw", "min_project_amount", "최소수주금액"
        ),
    )


# Anonymised client prefixes ("OO시", "OO광역시") and words that appear in
# almost every public project name, so they carry no capability signal.
_ORG_PREFIX = re.compile(r"^(?:OO|○○|◯◯|\*\*)[가-힣]*")
_GENERIC_TOKENS = frozenset(
    {
        "구축", "고도화", "용역", "사업", "시범사업", "개발", "공사", "조성공사",
        "운영", "기술", "이전", "노후", "도입", "지원", "관리", "서비스", "시스템",
    }
)


def _tech_stack(payload: dict, business_type: str | None) -> list[str]:
    """Capability keywords to match against a notice's text.

    The 나라장터 profile has no explicit tech stack, so it is derived from what
    the company has actually delivered. Past project names are the best source:
    they are written in the same vocabulary as the notices being screened
    ("지능형 CCTV 관제", "빅데이터 분석플랫폼"). Whole names are useless for
    substring matching, so they are reduced to their distinguishing tokens.
    """
    explicit = _listify(payload.get("tech_stack") or payload.get("역량") or payload.get("기술"))
    if explicit:
        return explicit

    keywords = [part.strip() for part in re.split(r"[·,/|]", business_type or "") if part.strip()]
    for name in _names(payload.get("track_records"), "project_name"):
        for token in name.split():
            token = _ORG_PREFIX.sub("", token).strip()
            if len(token) >= 3 and token not in _GENERIC_TOKENS:
                keywords.append(token)
    return _dedupe(keywords)


def _names(value: object, key: str) -> list[str]:
    """Flatten a list that may hold plain strings or objects with a name field."""
    if not isinstance(value, (list, tuple)):
        return _listify(value)
    names: list[str] = []
    for item in value:
        if isinstance(item, dict):
            name = item.get(key) or item.get("name") or item.get("title")
            if name:
                names.append(str(name).strip())
        elif str(item).strip():
            names.append(str(item).strip())
    return _dedupe(names)


def _first_str(payload: dict, *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", [], {}):
            return str(value).strip()
    return None


def _first_int(payload: dict, *keys: str) -> int:
    """Ints arrive as numbers or as digit strings like "500,000,000,000"."""
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            digits = re.sub(r"[^\d]", "", value)
            if digits:
                return int(digits)
    return 0


def _dedupe(values: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for value in values:
        seen.setdefault(value, None)
    return list(seen)


def _listify(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []
