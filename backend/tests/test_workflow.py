import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.rag.embeddings import HashingEmbeddings
from app.rag.chunker import chunk_markdown
from app.rag.retriever import Retriever
from app.rag.store import VectorStore
from app.samples import load_sample
from app.schemas import AgentRole, Decision
from app.supervisor import Supervisor

SETTINGS = Settings()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


async def test_retriever_gives_each_role_different_evidence():
    markdown = load_sample("2026-0101-sejong-shuttle")
    store = VectorStore(HashingEmbeddings())
    await store.index(chunk_markdown(markdown))
    retriever = Retriever(store, top_k=4)

    legal = await retriever.retrieve(["입찰참가 자격요건 및 제한사항"], ("자격",))
    finance = await retriever.retrieve(["사업 예산 및 대가 지급 방법"], ("예산", "지급"))

    assert legal and finance
    assert {c.chunk_id for c in legal} != {c.chunk_id for c in finance}
    assert any("자격" in c.section for c in legal)


async def test_go_case_produces_go_with_grounded_citations():
    result = await Supervisor(SETTINGS).run(load_sample("2026-0101-sejong-shuttle"), "sejong.md")

    assert result.committee.decision is Decision.GO
    assert len(result.opinions) == 4
    assert {o.role for o in result.opinions} == set(AgentRole)
    assert result.metrics.citation_validity_rate == 1.0
    assert all(o.citations for o in result.opinions)

    chunk_ids = {c.chunk_id for o in result.opinions for c in o.retrieved}
    cited = {c.chunk_id for o in result.opinions for c in o.citations}
    assert cited <= chunk_ids


async def test_region_restriction_triggers_legal_veto():
    result = await Supervisor(SETTINGS).run(load_sample("2026-0103-daegu-smartcity"), "daegu.md")

    legal = next(o for o in result.opinions if o.role is AgentRole.LEGAL)
    assert legal.decision is Decision.NO_GO
    assert result.committee.decision is Decision.NO_GO
    assert result.committee.human_review_required is True


async def test_low_value_maintenance_case_is_not_go():
    result = await Supervisor(SETTINGS).run(
        load_sample("2026-0104-anyang-signage"), "anyang.md"
    )

    finance = next(o for o in result.opinions if o.role is AgentRole.FINANCE)
    assert finance.decision is Decision.NO_GO
    assert result.committee.decision is not Decision.GO


async def test_stream_emits_stages_in_order():
    stages = [
        event.stage
        async for event in Supervisor(SETTINGS).stream(
            load_sample("2026-0101-sejong-shuttle"), "sejong.md"
        )
    ]
    assert stages[0] == "parsing"
    assert stages[1] == "indexing"
    assert stages.count("agent_started") == 4
    assert stages.count("agent_completed") == 4
    assert stages[-1] == "completed"
    assert stages.index("committee_completed") > stages.index("agent_completed")


def test_health_and_config_endpoints(client):
    assert client.get("/api/health").json()["status"] == "ok"
    config = client.get("/api/config").json()
    assert len(config["agents"]) == 4
    assert config["company"]["name"]


def test_samples_endpoint_lists_bundled_notices(client):
    ids = {s["id"] for s in client.get("/api/samples").json()["samples"]}
    assert "2026-0101-sejong-shuttle" in ids


def test_review_endpoint_returns_full_result(client):
    response = client.post("/api/review", json={"sample_id": "2026-0101-sejong-shuttle"})
    assert response.status_code == 200
    body = response.json()
    assert body["committee"]["decision"] == "GO"
    assert len(body["opinions"]) == 4


def test_review_rejects_empty_request(client):
    assert client.post("/api/review", json={}).status_code == 422


def test_review_rejects_unknown_sample(client):
    assert client.post("/api/review", json={"sample_id": "../../etc/passwd"}).status_code == 404


def test_stream_endpoint_emits_sse_frames(client):
    with client.stream(
        "POST", "/api/review/stream", json={"sample_id": "2026-0101-sejong-shuttle"}
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert "event: parsing" in body
    assert "event: completed" in body


def test_upload_converts_markdown(client):
    files = {"file": ("notice.md", b"# hi\n\n- gitea", "text/markdown")}
    body = client.post("/api/upload", files=files).json()
    assert body["document_name"] == "notice.md"
    assert "# hi" in body["markdown"]


def test_upload_rejects_unsupported_type(client):
    files = {"file": ("notice.exe", b"binary", "application/octet-stream")}
    assert client.post("/api/upload", files=files).status_code == 415
