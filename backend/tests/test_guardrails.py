from app.config import Settings
from app.guardrails import apply_guardrails, citation_stats, grounding_rate
from app.schemas import AgentOpinion, AgentRole, Citation, Decision, RetrievedChunk

SETTINGS = Settings(confidence_threshold=0.65, min_citations_per_opinion=1)
CHUNK = RetrievedChunk(
    chunk_id="c001",
    section="입찰참가 자격요건",
    text="소프트웨어사업자 신고를 필한 업체만 참가할 수 있다.",
    score=0.9,
)


def make_opinion(**overrides) -> AgentOpinion:
    base = dict(
        role=AgentRole.LEGAL,
        display_name="법무 담당 위원",
        perspective="Compliance Perspective",
        decision=Decision.GO,
        confidence=0.9,
        summary="자격요건을 충족한다.",
        strengths=["자격 충족"],
        risks=[],
        citations=[Citation(chunk_id="c001", section="", quote="소프트웨어사업자 신고를 필한 업체")],
    )
    base.update(overrides)
    return AgentOpinion(**base)


def test_valid_citation_passes_and_section_is_backfilled():
    result = apply_guardrails(make_opinion(), [CHUNK], SETTINGS)
    assert result.decision is Decision.GO
    assert result.citations[0].section == "입찰참가 자격요건"
    assert result.guardrail_flags == []


def test_hallucinated_chunk_id_is_dropped_and_downgraded():
    opinion = make_opinion(
        citations=[Citation(chunk_id="c999", section="", quote="존재하지 않는 근거")]
    )
    result = apply_guardrails(opinion, [CHUNK], SETTINGS)
    assert result.citations == []
    assert result.decision is Decision.REVIEW
    assert "invalid_citation:c999" in result.guardrail_flags
    assert "insufficient_citations" in result.guardrail_flags


def test_ungrounded_quote_is_replaced_with_source_snippet():
    opinion = make_opinion(
        citations=[Citation(chunk_id="c001", section="", quote="완전히 다른 문장 조작 인용")]
    )
    result = apply_guardrails(opinion, [CHUNK], SETTINGS)
    assert "ungrounded_quote:c001" in result.guardrail_flags
    assert result.citations[0].quote.startswith("소프트웨어사업자")


def test_low_confidence_go_is_downgraded_to_review():
    result = apply_guardrails(make_opinion(confidence=0.4), [CHUNK], SETTINGS)
    assert result.decision is Decision.REVIEW
    assert "low_confidence" in result.guardrail_flags


def test_no_evidence_is_flagged():
    result = apply_guardrails(make_opinion(), [], SETTINGS)
    assert "no_evidence_retrieved" in result.guardrail_flags
    assert result.decision is Decision.REVIEW


def test_metrics_count_valid_and_invalid_citations():
    good = apply_guardrails(make_opinion(), [CHUNK], SETTINGS)
    bad = apply_guardrails(
        make_opinion(citations=[Citation(chunk_id="c999", section="", quote="x")]),
        [CHUNK],
        SETTINGS,
    )
    total, valid = citation_stats([good, bad])
    assert (total, valid) == (2, 1)
    assert grounding_rate([good]) == 1.0
