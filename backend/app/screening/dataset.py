"""Loads the `projects/raw` corpus layout: bids/, bids_md/, bid_meta/."""

import json
import logging
from dataclasses import dataclass, field
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
            "duration": normalize.pick_str(self.meta, "duration"),
        }
        for key, value in overrides.items():
            if value:
                setattr(facts, key, value)

        budget = normalize.pick_budget(self.meta)
        if budget:
            facts.budget_krw = budget
        return facts


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

    revenue = normalize.pick(payload, "budget") or payload.get("annual_revenue") or 0
    return CompanyProfile(
        name=str(payload.get("name") or payload.get("회사명") or payload.get("company") or "당사"),
        headcount=int(payload.get("headcount") or payload.get("인력") or payload.get("임직원수") or 0),
        annual_revenue_krw=int(revenue) if str(revenue).isdigit() else 0,
        regions=normalize.pick_list(payload, "region") or _listify(payload.get("regions")),
        certifications=_listify(payload.get("certifications") or payload.get("자격") or payload.get("인증")),
        industry_codes=normalize.pick_list(payload, "industry_code"),
        tech_stack=_listify(payload.get("tech_stack") or payload.get("역량") or payload.get("기술")),
        past_projects=_listify(payload.get("past_projects") or payload.get("실적")),
    )


def _listify(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []
