import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.config import CORPUS_DIR, Settings
from app.main import app
from app.schemas import CompanyProfile, Recommendation
from app.screening.dataset import BidRecord, corpus_as_of, load_company, load_corpus
from app.screening.filters import prefilter
from app.screening.normalize import (
    parse_deadline,
    pick_budget,
    pick_duration,
    pick_list,
    pick_str,
)
from app.screening.screener import BatchScreener

CORPUS = CORPUS_DIR
TODAY = date(2026, 8, 5)
SETTINGS = Settings()

# The bundled corpus is an archive from 2025; screening it reproduces the day
# the last notice went up rather than the wall clock.
CORPUS_SIZE = 20
CORPUS_AS_OF = date(2025, 8, 3)

NOTICE = """# 테스트 공고

## 1. 사업 개요

- 사업예산: 900,000,000원
- 사업지역: 서울특별시

## 5. 입찰참가 자격요건

- 소프트웨어사업자 신고를 필한 업체
"""


@pytest.fixture
def company() -> CompanyProfile:
    """Synthetic profile: prefilter behaviour must not depend on the installed corpus."""
    return CompanyProfile(
        name="테스트 주식회사",
        headcount=500,
        annual_revenue_krw=100_000_000_000,
        regions=["서울", "경기"],
        certifications=["소프트웨어사업자 신고"],
        industry_codes=["6201", "7112"],
        tech_stack=["데이터 분석"],
        min_project_budget_krw=500_000_000,
        min_preparation_days=10,
        preferred_categories=["정보화사업", "용역"],
    )


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


def test_bid_date_is_read_as_the_submission_deadline():
    """나라장터 exports name the cut-off `bid_date`, not `deadline`."""
    assert pick_str({"bid_date": "2025-08-14"}, "deadline") == "2025-08-14"


def test_duration_falls_back_to_a_month_count():
    assert pick_duration({"사업기간": "12개월 (2025-08-25 ~ 2026-08-20)"}).startswith("12개월")
    assert pick_duration({"duration_months": 7}) == "7개월"
    assert pick_duration({}) is None


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


def test_off_strategy_category_warns_but_never_blocks(company):
    """Fit with the company's focus is a judgement call, so it goes to the committee."""
    outcome = prefilter(record({"마감일": "2026-09-01", "category": "물품구매"}), company, TODAY)
    assert not outcome.blocked
    assert any("비주력 분야" in warning for warning in outcome.warnings)


def test_preferred_category_raises_no_warning(company):
    outcome = prefilter(record({"마감일": "2026-09-01", "category": "정보화사업"}), company, TODAY)
    assert not any("비주력" in warning for warning in outcome.warnings)


def test_high_severity_risky_items_are_carried_into_warnings(company):
    outcome = prefilter(
        record(
            {
                "마감일": "2026-09-01",
                "risky_items": [
                    {"item": "예산규모", "risk": "대형사업 진입장벽", "severity": "high",
                     "desc": "컨소시엄 구성 필수"},
                    {"item": "가격배점", "risk": "저가수주 유도", "severity": "medium"},
                ],
            }
        ),
        company,
        TODAY,
    )
    assert not outcome.blocked
    assert any("대형사업 진입장벽" in w and "컨소시엄" in w for w in outcome.warnings)
    assert not any("저가수주" in w for w in outcome.warnings), "medium 리스크는 승계하지 않는다"


# --- corpus loading ---------------------------------------------------------


def test_corpus_loads_documents_joined_with_metadata():
    records = load_corpus(CORPUS)
    assert len(records) == CORPUS_SIZE
    assert all(item.meta for item in records), "every bid must join its metadata"

    storage = next(r for r in records if r.bid_id.endswith("20250013-3469"))
    facts = storage.facts()
    assert facts.agency == "조달청"
    assert facts.budget_krw == 23_451_000_000
    assert facts.deadline.startswith("2025-08-14")
    assert storage.category == "물품구매"


def test_metadata_overrides_document_parsing():
    item = record({"사업명": "메타 우선 사업명", "예산": 5_000_000_000})
    facts = item.facts()
    assert facts.title == "메타 우선 사업명"
    assert facts.budget_krw == 5_000_000_000


def test_scoring_table_becomes_evaluation_criteria():
    """배점표는 dict라 본문 불릿 파싱으로는 잡히지 않는다."""
    facts = record({"eval_criteria": {"기술능력": 50, "가격": 21}}).facts()
    assert "기술능력 50점" in facts.evaluation_criteria
    assert "가격 21점" in facts.evaluation_criteria


def test_company_profile_maps_the_narajangteo_shape():
    profile = load_company(CORPUS)
    assert profile is not None
    assert profile.name == "KIA 주식회사"
    assert profile.headcount == 38_000
    assert profile.technical_headcount == 450
    assert profile.capital_krw == 500_000_000_000
    assert profile.min_project_budget_krw == 1_000_000_000
    assert "정보화사업" in profile.preferred_categories
    # licenses[].name -> certifications, track_records[].project_name -> past_projects
    assert any("소프트웨어사업" in cert for cert in profile.certifications)
    assert any("스마트시티" in project for project in profile.past_projects)


def test_delivery_capacity_uses_engineers_not_total_headcount():
    profile = load_company(CORPUS)
    assert profile.delivery_headcount == 450, "38,000명 전체가 사업에 투입되지는 않는다"


def test_tech_stack_is_derived_from_past_project_names():
    profile = load_company(CORPUS)
    # Anonymised client prefixes and boilerplate must not become capabilities.
    assert "자율주행" in profile.tech_stack
    assert "빅데이터" in profile.tech_stack
    assert not any(token.startswith("OO") for token in profile.tech_stack)
    assert "구축" not in profile.tech_stack


def test_corpus_as_of_is_the_last_announcement():
    assert corpus_as_of(load_corpus(CORPUS)) == CORPUS_AS_OF


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


# --- as-of resolution -------------------------------------------------------


def test_as_of_prefers_an_explicit_setting():
    screener = BatchScreener(Settings(as_of="2025-08-20"))
    as_of, source = screener.resolve_as_of(load_corpus(CORPUS))
    assert (as_of, source) == (date(2025, 8, 20), "configured")


def test_as_of_falls_back_to_the_corpus_window():
    as_of, source = BatchScreener(SETTINGS).resolve_as_of(load_corpus(CORPUS))
    assert (as_of, source) == (CORPUS_AS_OF, "corpus")


def test_as_of_uses_today_when_the_corpus_has_no_dates():
    as_of, source = BatchScreener(SETTINGS).resolve_as_of([record({})])
    assert (as_of, source) == (date.today(), "today")


def test_as_of_today_keyword_tracks_the_wall_clock():
    assert Settings(as_of="today").as_of_date == date.today()


def test_as_of_rejects_an_unparseable_date():
    with pytest.raises(ValueError, match="BIDCOM_AS_OF"):
        _ = Settings(as_of="2025/08/20").as_of_date


# --- batch screening --------------------------------------------------------


async def test_screening_the_archive_does_not_expire_every_bid():
    """The regression this guards: judged against today, all 20 are 마감경과."""
    report = await BatchScreener(SETTINGS).screen_corpus(CORPUS)

    assert report.total == CORPUS_SIZE
    assert report.as_of == CORPUS_AS_OF.isoformat()
    assert report.as_of_source == "corpus"
    assert report.filtered_out == 0
    assert report.screened_by_committee == CORPUS_SIZE
    assert report.company == "KIA 주식회사"
    assert all(item.days_left is not None and item.days_left >= 0 for item in report.items)


async def test_an_explicit_today_still_wins():
    report = await BatchScreener(SETTINGS).screen_corpus(CORPUS, today=TODAY)
    assert report.filtered_out == CORPUS_SIZE, "2026년 기준으로는 전부 마감경과"
    assert all(item.recommendation is Recommendation.PASS for item in report.items)


async def test_blocked_bids_never_reach_the_committee():
    report = await BatchScreener(SETTINGS).screen_corpus(CORPUS, today=TODAY)
    blocked = [item for item in report.items if item.screen.blocked]
    assert blocked
    assert all(item.committee is None for item in blocked)
    assert all(item.agent_decisions == {} for item in blocked)


async def test_bids_matching_past_delivery_rank_highest():
    """KIA has delivered CCTV 관제, 빅데이터, 블록체인 인증 — those should surface."""
    report = await BatchScreener(SETTINGS).screen_corpus(CORPUS)
    recommended = {
        item.bid_id for item in report.items if item.recommendation is Recommendation.STRONG
    }
    assert recommended, "실적과 겹치는 공고는 적극추천으로 올라와야 한다"
    assert any("CCTV" in bid_id for bid_id in recommended)
    assert any("빅데이터" in bid_id for bid_id in recommended)


async def test_ranking_is_tier_then_deadline():
    report = await BatchScreener(SETTINGS).screen_corpus(CORPUS)
    recommended = [i for i in report.items if i.recommendation is Recommendation.STRONG]
    assert [i.days_left for i in recommended] == sorted(i.days_left for i in recommended)


async def test_recommended_bids_carry_committee_evidence():
    report = await BatchScreener(SETTINGS).screen_corpus(CORPUS)
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
    assert body["count"] == CORPUS_SIZE
    assert body["company"]["name"] == "KIA 주식회사"


def test_screen_endpoint_returns_full_report(client):
    body = client.post("/api/screen").json()
    assert body["total"] == CORPUS_SIZE
    assert sum(body["counts"].values()) == CORPUS_SIZE
    assert len(body["items"]) == CORPUS_SIZE
    assert body["as_of"] == CORPUS_AS_OF.isoformat()
    assert body["items"][0]["recommendation"] in {"적극추천", "검토", "패스"}
