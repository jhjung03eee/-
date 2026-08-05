import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.config import DATA_DIR, Settings
from app.main import app
from app.schemas import Recommendation
from app.screening.dataset import BidRecord, load_company, load_corpus
from app.screening.filters import prefilter
from app.screening.normalize import parse_deadline, pick_budget, pick_list, pick_str
from app.screening.screener import BatchScreener

CORPUS = DATA_DIR / "demo_corpus"
TODAY = date(2026, 8, 5)
SETTINGS = Settings()

NOTICE = """# 테스트 공고

## 1. 사업 개요

- 사업예산: 900,000,000원
- 사업지역: 서울특별시

## 5. 입찰참가 자격요건

- 소프트웨어사업자 신고를 필한 업체
"""


@pytest.fixture
def company():
    profile = load_company(CORPUS)
    assert profile is not None
    return profile


def record(meta: dict, markdown: str = NOTICE) -> BidRecord:
    return BidRecord(bid_id="test-bid", markdown=markdown, meta=meta)


# --- metadata normalization -------------------------------------------------


def test_normalize_accepts_korean_and_english_keys():
    assert pick_str({"발주처": "서울시"}, "agency") == "서울시"
    assert pick_str({"agency": "서울시"}, "agency") == "서울시"
    assert pick_str({"AGENCY": "서울시"}, "agency") == "서울시"
    assert pick_str({"unrelated": "x"}, "agency") is None


def test_normalize_budget_from_number_or_text():
    assert pick_budget({"예산": 920000000}) == 920_000_000
    assert pick_budget({"budget": "9.2억원"}) == 920_000_000
    assert pick_budget({}) is None


def test_normalize_industry_codes_from_string_or_list():
    assert pick_list({"업종코드": "6201, 7112"}, "industry_code") == ["6201", "7112"]
    assert pick_list({"industry_code": ["6201"]}, "industry_code") == ["6201"]


@pytest.mark.parametrize(
    "value",
    ["2026-09-02", "2026.09.02", "2026/09/02", "20260902", "2026-09-02 16:00", "2026년 9월 2일"],
)
def test_parse_deadline_accepts_common_formats(value):
    assert parse_deadline(value) == date(2026, 9, 2)


def test_parse_deadline_returns_none_for_garbage():
    assert parse_deadline("추후 공고") is None
    assert parse_deadline(None) is None


# --- prefilters -------------------------------------------------------------


def test_expired_deadline_is_blocked(company):
    outcome = prefilter(record({"마감일": "2026-07-20"}), company, TODAY)
    assert outcome.blocked
    assert any("마감경과" in reason for reason in outcome.block_reasons)


def test_imminent_deadline_warns_but_does_not_block(company):
    outcome = prefilter(record({"마감일": "2026-08-10"}), company, TODAY)
    assert not outcome.blocked
    assert outcome.urgent
    assert outcome.days_left == 5


def test_budget_below_threshold_is_blocked(company):
    outcome = prefilter(record({"마감일": "2026-09-01", "예산": 120_000_000}), company, TODAY)
    assert outcome.blocked
    assert any("예산미달" in reason for reason in outcome.block_reasons)


def test_unheld_industry_code_is_blocked(company):
    outcome = prefilter(record({"마감일": "2026-09-01", "업종코드": "4290"}), company, TODAY)
    assert outcome.blocked
    assert any("업종코드" in reason for reason in outcome.block_reasons)


def test_held_industry_code_passes(company):
    outcome = prefilter(record({"마감일": "2026-09-01", "업종코드": "6201"}), company, TODAY)
    assert not outcome.blocked


def test_region_restriction_outside_footprint_is_blocked(company):
    restricted = NOTICE.replace("서울특별시", "대구광역시") + "\n본 입찰은 지역제한 경쟁입찰이다."
    outcome = prefilter(record({"마감일": "2026-09-01"}, restricted), company, TODAY)
    assert outcome.blocked
    assert any("지역제한" in reason for reason in outcome.block_reasons)


def test_missing_fields_warn_instead_of_blocking(company):
    outcome = prefilter(record({}, "# 제목만 있는 공고"), company, TODAY)
    assert not outcome.blocked
    assert outcome.warnings


# --- corpus loading ---------------------------------------------------------


def test_corpus_loads_documents_joined_with_metadata():
    records = load_corpus(CORPUS)
    assert len(records) == 8
    assert all(record.meta for record in records), "every demo bid must join its metadata"

    busan = next(r for r in records if r.bid_id == "2026-0105-busan-drt")
    facts = busan.facts()
    assert facts.agency == "부산광역시 교통혁신본부"
    assert facts.budget_krw == 1_250_000_000


def test_metadata_overrides_document_parsing():
    item = record({"사업명": "메타 우선 사업명", "예산": 5_000_000_000})
    facts = item.facts()
    assert facts.title == "메타 우선 사업명"
    assert facts.budget_krw == 5_000_000_000


def test_company_profile_maps_kia_fields(company):
    assert company.name.startswith("기아")
    assert "6201" in company.industry_codes
    assert company.min_preparation_days == 10


def test_corpus_tolerates_metadata_keyed_by_bid_number(tmp_path):
    (tmp_path / "bids_md").mkdir()
    (tmp_path / "bid_meta").mkdir()
    (tmp_path / "bids_md" / "notice-a.md").write_text(NOTICE, encoding="utf-8")
    (tmp_path / "bid_meta" / "notice-a.json").write_text(
        json.dumps({"공고번호": "20260101-00", "발주처": "테스트청"}, ensure_ascii=False),
        encoding="utf-8",
    )
    records = load_corpus(tmp_path)
    assert len(records) == 1
    assert records[0].facts().agency == "테스트청"


def test_corpus_survives_malformed_metadata(tmp_path):
    (tmp_path / "bids_md").mkdir()
    (tmp_path / "bid_meta").mkdir()
    (tmp_path / "bids_md" / "notice-a.md").write_text(NOTICE, encoding="utf-8")
    (tmp_path / "bid_meta" / "broken.json").write_text("{not json", encoding="utf-8")
    records = load_corpus(tmp_path)
    assert len(records) == 1
    assert records[0].meta == {}


# --- batch screening --------------------------------------------------------


async def test_batch_screening_ranks_and_filters(company):
    report = await BatchScreener(SETTINGS).screen_corpus(CORPUS, today=TODAY)

    assert report.total == 8
    assert report.filtered_out == 4
    assert report.screened_by_committee == 4
    assert report.company.startswith("기아")

    by_id = {item.bid_id: item for item in report.items}
    assert by_id["2026-0108-ulsan-expired"].recommendation is Recommendation.PASS
    assert by_id["2026-0104-anyang-signage"].recommendation is Recommendation.PASS
    assert by_id["2026-0103-daegu-smartcity"].recommendation is Recommendation.PASS
    assert by_id["2026-0106-jeju-ev"].recommendation is Recommendation.PASS
    assert by_id["2026-0101-sejong-shuttle"].recommendation is Recommendation.STRONG


async def test_blocked_bids_never_reach_the_committee():
    report = await BatchScreener(SETTINGS).screen_corpus(CORPUS, today=TODAY)
    blocked = [item for item in report.items if item.screen.blocked]
    assert blocked
    assert all(item.committee is None for item in blocked)
    assert all(item.agent_decisions == {} for item in blocked)


async def test_imminent_deadline_is_ranked_first_within_its_tier():
    report = await BatchScreener(SETTINGS).screen_corpus(CORPUS, today=TODAY)
    recommended = [i for i in report.items if i.recommendation is Recommendation.STRONG]
    assert recommended[0].bid_id == "2026-0105-busan-drt"
    assert recommended[0].urgent
    assert [i.days_left for i in recommended] == sorted(i.days_left for i in recommended)


async def test_recommended_bids_carry_committee_evidence():
    report = await BatchScreener(SETTINGS).screen_corpus(CORPUS, today=TODAY)
    for item in report.items:
        if item.committee:
            assert item.committee.votes
            assert item.committee.executive_summary
            assert len(item.agent_decisions) == 4


# --- API --------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_corpus_endpoint_lists_bids(client):
    body = client.get("/api/corpus").json()
    assert body["available"] is True
    assert body["count"] == 8
    assert body["company"]["name"].startswith("기아")


def test_screen_endpoint_returns_full_report(client):
    body = client.post("/api/screen").json()
    assert body["total"] == 8
    assert sum(body["counts"].values()) == 8
    assert len(body["items"]) == 8
    assert body["items"][0]["recommendation"] in {"적극추천", "검토", "패스"}
