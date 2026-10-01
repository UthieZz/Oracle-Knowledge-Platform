"""SQLite persistence adapter for agent feedback.

Feedback remains process/audit data. This adapter does not write into
KnowledgePackage and does not promote memory candidates.
"""
from __future__ import annotations

import sqlite3
from typing import List, Optional

from okc.agent.feedback import (
    AgentFeedbackPackage,
    FeedbackAcceptanceError,
    FeedbackLedger,
)


class SQLiteFeedbackLedger(FeedbackLedger):
    """Durable FeedbackLedger with tenant/silo isolation on read."""

    def __init__(self, db_path: str = "okp_local.db") -> None:
        super().__init__()
        self.db_path = db_path
        self._init_db()
        self._load()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_feedback (
                    request_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    silo_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (request_id, tenant_id, silo_id)
                )
                """
            )
            conn.commit()

    def _load(self) -> None:
        self.records = []
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT payload_json FROM agent_feedback ORDER BY received_at ASC"
            ).fetchall()
        for (payload,) in rows:
            self.records.append(AgentFeedbackPackage.model_validate_json(payload))

    def accept(self, feedback: AgentFeedbackPackage) -> AgentFeedbackPackage:
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                """
                SELECT 1 FROM agent_feedback
                WHERE request_id = ? AND tenant_id = ? AND silo_id = ?
                """,
                (feedback.request_id, feedback.tenant_id, feedback.silo_id),
            ).fetchone()
        if existing:
            raise FeedbackAcceptanceError(
                "Feedback request_id already stored for this tenant/silo."
            )
        stored = super().accept(feedback)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO agent_feedback
                (request_id, tenant_id, silo_id, agent_id, received_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    stored.request_id,
                    stored.tenant_id,
                    stored.silo_id,
                    stored.agent_id,
                    stored.received_at,
                    stored.model_dump_json(),
                ),
            )
            conn.commit()
        return stored

    def list_for(self, tenant_id: str, silo_id: str) -> List[AgentFeedbackPackage]:
        if not tenant_id or not silo_id:
            raise FeedbackAcceptanceError("tenant_id and silo_id are required.")
        return [
            rec
            for rec in self.records
            if rec.tenant_id == tenant_id and rec.silo_id == silo_id
        ]

    def get(
        self, request_id: str, tenant_id: str, silo_id: str
    ) -> Optional[AgentFeedbackPackage]:
        if not request_id or not tenant_id or not silo_id:
            raise FeedbackAcceptanceError("request, tenant, and silo identity required.")
        for rec in self.records:
            if (
                rec.request_id == request_id
                and rec.tenant_id == tenant_id
                and rec.silo_id == silo_id
            ):
                return rec
        return None
