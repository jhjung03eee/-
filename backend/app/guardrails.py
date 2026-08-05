import re

from app.config import Settings
from app.schemas import AgentOpinion, Citation, Decision, RetrievedChunk

_TOKEN = re.compile(r"[0-9a-zA-Z가-힣]+")
GROUNDING_OVERLAP_THRESHOLD = 0.6


def apply_guardrails(
    opinion: AgentOpinion, retrieved: list[RetrievedChunk], settings: Settings
) -> AgentOpinion:
    by_id = {chunk.chunk_id: chunk for chunk in retrieved}
    flags = list(opinion.guardrail_flags)

    valid: list[Citation] = []
    for citation in opinion.citations:
        chunk = by_id.get(citation.chunk_id)
        if chunk is None:
            flags.append(f"invalid_citation:{citation.chunk_id}")
            continue
        if citation.quote and not _is_grounded(citation.quote, chunk.text):
            flags.append(f"ungrounded_quote:{citation.chunk_id}")
            citation = citation.model_copy(update={"quote": _snippet(chunk.text)})
        valid.append(citation.model_copy(update={"section": chunk.section}))

    opinion.citations = valid

    if not retrieved:
        flags.append("no_evidence_retrieved")
    if len(valid) < settings.min_citations_per_opinion:
        flags.append("insufficient_citations")
        if opinion.decision is not Decision.REVIEW:
            flags.append(f"downgraded_from:{opinion.decision.value}")
            opinion.decision = Decision.REVIEW
        opinion.confidence = min(opinion.confidence, 0.5)

    if opinion.confidence < settings.confidence_threshold:
        flags.append("low_confidence")
        if opinion.decision is not Decision.REVIEW:
            flags.append(f"downgraded_from:{opinion.decision.value}")
            opinion.decision = Decision.REVIEW

    opinion.guardrail_flags = flags
    return opinion


def _is_grounded(quote: str, source: str) -> bool:
    quote_tokens = set(_TOKEN.findall(quote.lower()))
    if not quote_tokens:
        return False
    source_tokens = set(_TOKEN.findall(source.lower()))
    overlap = len(quote_tokens & source_tokens) / len(quote_tokens)
    return overlap >= GROUNDING_OVERLAP_THRESHOLD


def _snippet(text: str, limit: int = 180) -> str:
    return " ".join(text.split())[:limit]


def grounding_rate(opinions: list[AgentOpinion]) -> float:
    """Share of claims (strengths + risks) backed by at least one valid citation."""
    total = sum(len(o.strengths) + len(o.risks) for o in opinions)
    if not total:
        return 0.0
    grounded = sum(
        (len(o.strengths) + len(o.risks)) for o in opinions if o.citations
    )
    return round(grounded / total, 3)


def citation_stats(opinions: list[AgentOpinion]) -> tuple[int, int]:
    valid = sum(len(o.citations) for o in opinions)
    invalid = sum(1 for o in opinions for f in o.guardrail_flags if f.startswith("invalid_citation"))
    return valid + invalid, valid
