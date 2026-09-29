"""Persistence adapters for AgentFeedbackPackage.

Feedback remains process/audit data. Persistence must not write
memory candidates into KnowledgePackage or knowledge_objects tables.
"""
from __future__ import annotations

import sqlite3
from typing import List, Optional

from okc.agent.feedback import AgentFeedbackPackage, FeedbackLedger


class SQLiteFeedbackStore:
    """Durable ledger for accepted agent feedback.

    Isolation: list/get filter by tenant_id and silo_id.
    Promotion: never sets MemoryCandidate.accepted and never
    inserts into knowledge tables.
    """

    def __init__(self, db_path: str, ledger: Optional[FeedbackLedger] = None) -> None:
        self.db_path = db_path
        self.ledger = ledger or FeedbackLedger()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_feedback (
                    request_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    silo_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    raw_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_agent_feedback_tenant_silo "
                "ON agent_feedback (tenant_id, silo_id)"
            )
            conn.commit()

    def accept(self, feedback: AgentFeedbackPackage) -> AgentFeedbackPackage:
        stored = self.ledger.accept(feedback)
        payload = stored.model_dump_json()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO agent_feedback
                (request_id, tenant_id, silo_id, agent_id, received_at, raw_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    stored.request_id,
                    stored.tenant_id,
                    stored.silo_id,
                    stored.agent_id,
                    stored.received_at,
                    payload,
                ),
            )
            conn.commit()
        return stored

    def get(
        self, request_id: str, tenant_id: str, silo_id: str
    ) -> Optional[AgentFeedbackPackage]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT raw_json FROM agent_feedback
                WHERE request_id = ? AND tenant_id = ? AND silo_id = ?
                """,
                (request_id, tenant_id, silo_id),
            ).fetchone()
        if row is None:
            return None
        return AgentFeedbackPackage.model_validate_json(row[0])

    def list(
        self, tenant_id: str, silo_id: str
    ) -> List[AgentFeedbackPackage]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT raw_json FROM agent_feedback
                WHERE tenant_id = ? AND silo_id = ?
                ORDER BY received_at ASC
                """,
                (tenant_id, silo_id),
            ).fetchall()
        return [AgentFeedbackPackage.model_validate_json(row[0]) for row in rows]
