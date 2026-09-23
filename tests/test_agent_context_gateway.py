from okc.agent import ContextGateway, AgentContextRequest, ContextAccessError
from okc.models.knowledge_package import EvidenceSpan, KnowledgeObject, Provenance

class StubRetriever:
    def __init__(self, objects):
        self.objects = objects
    def retrieve(self, request):
        return self.objects

def make_object(tenant="acme", silo="finance"):
    return KnowledgeObject(
        object_id="ko_1",
        title="Transfer policy",
        content="International transfers require the applicable verification step.",
        provenance=Provenance(
            source_platform="test",
            source_file="policy.md",
            source_record_ids=["r1"],
            tenant_id=tenant,
            silo_id=silo,
        ),
        evidence=[EvidenceSpan(
            span_id="span_1",
            message_id="msg_1",
            role="source",
            timestamp="2026-09-23T00:00:00Z",
            content="International transfers require the applicable verification step.",
        )],
    )

def test_build_returns_model_facing_context_with_provenance():
    request = AgentContextRequest(
        request_id="req_1", tenant_id="acme", silo_id="finance",
        agent_id="agent_1", task="Explain the transfer policy."
    )
    package = ContextGateway(StubRetriever([make_object()])).build(request)
    assert package.schema_version == "1.0.0"
    assert package.items[0].object_id == "ko_1"
    assert package.provenance_complete is True
    assert package.items[0].provenance["source_file"] == "policy.md"

def test_gateway_rejects_cross_silo_context():
    request = AgentContextRequest(
        request_id="req_2", tenant_id="acme", silo_id="finance",
        agent_id="agent_1", task="Explain the policy."
    )
    try:
        ContextGateway(StubRetriever([make_object(tenant="acme", silo="legal")])).build(request)
    except ContextAccessError:
        return
    raise AssertionError("Cross-silo KnowledgeObject was not rejected.")
