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


def test_gateway_respects_strict_retriever_missing_permission():
    """P1 boundary: ContextGateway does not reintroduce objects denied by a strict-mode retriever.
    Missing permission entry is treated as denial when the retriever is constructed with strict_permissions=True.
    """
    from okc.connect.knowledge_accumulator import KnowledgeAccumulator
    from okc.connect.interfaces import SyncEvent
    from okc.agent.retrievers import KnowledgePackageRetriever

    acc = KnowledgeAccumulator()
    create = SyncEvent(
        event_id="c1",
        source="folder",
        kind="create",
        payload={"object_id": "doc1", "text": "restricted knowledge"},
        tenant_id="acme",
        silo_id="finance",
    )
    acc.process(create)

    # Strict retriever denies objects lacking an explicit permission entry
    retriever = KnowledgePackageRetriever(acc.package, strict_permissions=True)
    request = AgentContextRequest(
        request_id="req_strict",
        tenant_id="acme",
        silo_id="finance",
        agent_id="agent_1",
        task="restricted knowledge",
    )
    package = ContextGateway(retriever).build(request)
    assert len(package.items) == 0

    # Explicit allow restores the object through the same gateway path
    allow = SyncEvent(
        event_id="p1",
        source="folder",
        kind="permission_change",
        payload={"object_id": "doc1", "read": True},
        tenant_id="acme",
        silo_id="finance",
    )
    acc.process(allow)
    package_allowed = ContextGateway(retriever).build(request)
    assert len(package_allowed.items) == 1
    assert package_allowed.items[0].title or package_allowed.items[0].content


def test_gateway_respects_revocation_after_prior_retrieval():
    """P1: Explicit read=False after prior successful retrieval excludes the object on subsequent gateway builds.
    Confirms no improper caching; permission map is consulted on every retrieve.
    """
    from okc.connect.knowledge_accumulator import KnowledgeAccumulator
    from okc.connect.interfaces import SyncEvent
    from okc.agent.retrievers import KnowledgePackageRetriever

    acc = KnowledgeAccumulator()
    create = SyncEvent(
        event_id="c1",
        source="folder",
        kind="create",
        payload={"object_id": "doc1", "text": "visible knowledge"},
        tenant_id="acme",
        silo_id="finance",
    )
    acc.process(create)

    retriever = KnowledgePackageRetriever(acc.package)  # default (pilot) mode
    request = AgentContextRequest(
        request_id="req_revoke",
        tenant_id="acme",
        silo_id="finance",
        agent_id="agent_1",
        task="visible knowledge",
    )
    # Prior retrieval succeeds
    package_before = ContextGateway(retriever).build(request)
    assert len(package_before.items) == 1

    # Revoke
    deny = SyncEvent(
        event_id="p_deny",
        source="folder",
        kind="permission_change",
        payload={"object_id": "doc1", "read": False},
        tenant_id="acme",
        silo_id="finance",
    )
    acc.process(deny)

    # Subsequent build excludes it
    package_after = ContextGateway(retriever).build(request)
    assert len(package_after.items) == 0
