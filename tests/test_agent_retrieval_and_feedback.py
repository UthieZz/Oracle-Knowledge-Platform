from okc.agent import (
    AgentContextRequest,
    AgentFeedbackPackage,
    CitationEvent,
    ContextGateway,
    FeedbackAcceptanceError,
    FeedbackLedger,
    SQLiteFeedbackLedger,
    KnowledgePackageRetriever,
    MemoryCandidate,
    ToolEvent,
    AuditRecord,
)
from okc.models.knowledge_package import EvidenceSpan, KnowledgeObject, KnowledgePackage, Provenance


def _obj(object_id, title, content, tenant="acme", silo="finance"):
    return KnowledgeObject(
        object_id=object_id,
        title=title,
        content=content,
        provenance=Provenance(
            source_platform="test",
            source_file=f"{object_id}.md",
            source_record_ids=[object_id],
            tenant_id=tenant,
            silo_id=silo,
        ),
        evidence=[EvidenceSpan(
            span_id=f"{object_id}_span",
            message_id=f"{object_id}_msg",
            role="source",
            timestamp="2026-09-23T00:00:00Z",
            content=content,
        )],
    )


def _package():
    return KnowledgePackage(
        package_id="pkg_1",
        objects=[
            _obj("ko_transfer", "Transfer policy", "International transfers require verification."),
            _obj("ko_leave", "Leave policy", "Annual leave accrues monthly."),
            _obj("ko_legal", "Litigation hold", "Do not delete legal records.", silo="legal"),
        ],
    )


def test_package_retriever_ranks_task_overlap_and_keeps_silo():
    request = AgentContextRequest(
        request_id="req_r1",
        tenant_id="acme",
        silo_id="finance",
        agent_id="agent_1",
        task="Explain international transfers",
    )
    retrieved = KnowledgePackageRetriever(_package()).retrieve(request)
    ids = [obj.object_id for obj in retrieved]
    assert ids[0] == "ko_transfer"
    assert "ko_legal" not in ids
    assert "ko_leave" in ids


def test_gateway_uses_package_retriever_without_cross_silo_leak():
    request = AgentContextRequest(
        request_id="req_r2",
        tenant_id="acme",
        silo_id="finance",
        agent_id="agent_1",
        task="Explain international transfers",
    )
    package = ContextGateway(KnowledgePackageRetriever(_package())).build(request)
    assert package.items[0].object_id == "ko_transfer"
    assert package.provenance_complete is True
    assert all(item.provenance["silo_id"] == "finance" for item in package.items)


def test_feedback_ledger_accepts_citations_and_tool_events():
    ledger = FeedbackLedger()
    accepted = ledger.accept(AgentFeedbackPackage(
        request_id="req_r3",
        tenant_id="acme",
        silo_id="finance",
        agent_id="agent_1",
        citations=[CitationEvent(object_id="ko_transfer", evidence_ids=["ko_transfer_span"])],
        tool_events=[ToolEvent(tool_name="lookup_policy", status="succeeded")],
        memory_candidates=[MemoryCandidate(candidate_id="mem_1", text="Transfers need verification")],
        audit=[AuditRecord(event_type="context_used", detail={"request_id": "req_r3"})],
    ))
    assert accepted.citations[0].object_id == "ko_transfer"
    assert accepted.memory_candidates[0].accepted is False
    assert len(ledger.records) == 1


def test_feedback_rejects_premature_memory_promotion():
    ledger = FeedbackLedger()
    try:
        ledger.accept(AgentFeedbackPackage(
            request_id="req_r4",
            tenant_id="acme",
            silo_id="finance",
            agent_id="agent_1",
            memory_candidates=[MemoryCandidate(
                candidate_id="mem_2",
                text="Promote me",
                accepted=True,
            )],
        ))
    except FeedbackAcceptanceError:
        return
    raise AssertionError("Accepted memory candidate crossed the canonical-knowledge boundary.")


def test_sqlite_feedback_ledger_persists_and_isolates(tmp_path):
    db = tmp_path / "feedback.db"
    ledger = SQLiteFeedbackLedger(str(db))
    ledger.accept(AgentFeedbackPackage(
        request_id="req_persist",
        tenant_id="acme",
        silo_id="finance",
        agent_id="agent_1",
        memory_candidates=[MemoryCandidate(candidate_id="mem_p", text="candidate only")],
    ))
    reopened = SQLiteFeedbackLedger(str(db))
    found = reopened.get("req_persist", "acme", "finance")
    assert found is not None
    assert found.memory_candidates[0].accepted is False
    assert reopened.list_for("acme", "legal") == []
    assert reopened.get("req_persist", "acme", "legal") is None


def test_sqlite_feedback_rejects_duplicate_request_id(tmp_path):
    db = tmp_path / "feedback.db"
    ledger = SQLiteFeedbackLedger(str(db))
    payload = dict(
        request_id="req_dup",
        tenant_id="acme",
        silo_id="finance",
        agent_id="agent_1",
    )
    ledger.accept(AgentFeedbackPackage(**payload))
    try:
        ledger.accept(AgentFeedbackPackage(**payload))
    except FeedbackAcceptanceError:
        assert len(ledger.list_for("acme", "finance")) == 1
        return
    raise AssertionError("Duplicate feedback request was stored.")
