import pytest

from app.agents.chair import CommitteeChair
from app.config import Settings
from app.llm.mock import HeuristicClient
from app.schemas import AgentOpinion, AgentRole, BidFacts, Citation, Decision

SETTINGS = Settings(confidence_threshold=0.65)
FACTS = BidFacts(title="테스트 사업", budget_krw=1_000_000_000)

ROLE_NAMES = {
    AgentRole.SALES: "영업 담당 위원",
    AgentRole.TECHNICAL: "기술 담당 위원",
    AgentRole.FINANCE: "재무 담당 위원",
    AgentRole.LEGAL: "법무 담당 위원",
}


def opinion(role: AgentRole, decision: Decision, confidence: float = 0.9) -> AgentOpinion:
    return AgentOpinion(
        role=role,
        display_name=ROLE_NAMES[role],
        perspective="test",
        decision=decision,
        confidence=confidence,
        summary=f"{role.value} 판단",
        citations=[Citation(chunk_id="c001", section="s", quote="q")],
    )


@pytest.fixture
def chair() -> CommitteeChair:
    return CommitteeChair(HeuristicClient(), SETTINGS)


async def test_unanimous_go(chair):
    opinions = [opinion(role, Decision.GO) for role in AgentRole]
    result = await chair.decide(opinions, FACTS)
    assert result.decision is Decision.GO
    assert result.priority >= 4
    assert result.dissenting_roles == []


async def test_unanimous_no_go(chair):
    opinions = [opinion(role, Decision.NO_GO) for role in AgentRole]
    result = await chair.decide(opinions, FACTS)
    assert result.decision is Decision.NO_GO
    assert result.priority == 1


async def test_legal_veto_overrides_majority_go(chair):
    opinions = [
        opinion(AgentRole.SALES, Decision.GO),
        opinion(AgentRole.TECHNICAL, Decision.GO),
        opinion(AgentRole.FINANCE, Decision.GO),
        opinion(AgentRole.LEGAL, Decision.NO_GO, confidence=0.85),
    ]
    result = await chair.decide(opinions, FACTS)
    assert result.decision is Decision.NO_GO
    assert AgentRole.LEGAL not in result.dissenting_roles
    assert result.human_review_required is True


async def test_low_confidence_legal_no_go_does_not_veto(chair):
    opinions = [
        opinion(AgentRole.SALES, Decision.GO),
        opinion(AgentRole.TECHNICAL, Decision.GO),
        opinion(AgentRole.FINANCE, Decision.GO),
        opinion(AgentRole.LEGAL, Decision.NO_GO, confidence=0.5),
    ]
    result = await chair.decide(opinions, FACTS)
    assert result.decision is not Decision.NO_GO


async def test_low_confidence_votes_carry_less_weight(chair):
    confident = await chair.decide([opinion(r, Decision.GO, 0.95) for r in AgentRole], FACTS)
    unsure = await chair.decide([opinion(r, Decision.GO, 0.2) for r in AgentRole], FACTS)
    assert confident.confidence > unsure.confidence
    assert unsure.human_review_required is True


async def test_split_vote_requires_human_review(chair):
    opinions = [
        opinion(AgentRole.SALES, Decision.GO),
        opinion(AgentRole.TECHNICAL, Decision.NO_GO),
        opinion(AgentRole.FINANCE, Decision.REVIEW),
        opinion(AgentRole.LEGAL, Decision.REVIEW),
    ]
    result = await chair.decide(opinions, FACTS)
    assert result.human_review_required is True
    assert any("충돌" in reason for reason in result.human_review_reasons)
