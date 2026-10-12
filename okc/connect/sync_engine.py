"""Persistent sync engine for OKP Connect.

Durable SQLite queue for SyncEvents. Cursor tracking, idempotency via event_id,
retry/attempt counting, status audit. Does not write KnowledgePackage.
Callers supply an ingestion processor that consumes processed events.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Callable, List, Optional

from okc.connect.interfaces import SyncEvent


class SyncEngineError(ValueError):
    """Sync engine refused an operation."""


class SyncEngine:
    """SQLite-backed durable queue and cursor store for Connect events."""

    def __init__(self, db_path: str = "okp_connect.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_events (
                    event_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    cursor TEXT,
                    payload_json TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    silo_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_cursors (
                    source TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    silo_id TEXT NOT NULL,
                    cursor TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (source, tenant_id, silo_id)
                )
                """
            )
            conn.commit()

    def enqueue(self, event: SyncEvent) -> bool:
        """Insert event if event_id is new. Returns True if inserted, False if duplicate."""
        if not event.event_id or not event.tenant_id or not event.silo_id:
            raise SyncEngineError("event_id, tenant_id, and silo_id are required.")
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(event.payload or {})
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO sync_events
                    (event_id, source, kind, cursor, payload_json, occurred_at,
                     tenant_id, silo_id, status, attempts, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', 0, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.source,
                        event.kind,
                        event.cursor,
                        payload,
                        event.occurred_at,
                        event.tenant_id,
                        event.silo_id,
                        now,
                        now,
                    ),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_cursor(self, source: str, tenant_id: str, silo_id: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT cursor FROM sync_cursors
                WHERE source = ? AND tenant_id = ? AND silo_id = ?
                """,
                (source, tenant_id, silo_id),
            ).fetchone()
        return row[0] if row else None

    def set_cursor(self, source: str, tenant_id: str, silo_id: str, cursor: str) -> None:
        if not source or not tenant_id or not silo_id or cursor is None:
            raise SyncEngineError("source, tenant_id, silo_id, and cursor are required.")
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO sync_cursors (source, tenant_id, silo_id, cursor, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source, tenant_id, silo_id) DO UPDATE SET
                    cursor = excluded.cursor,
                    updated_at = excluded.updated_at
                """,
                (source, tenant_id, silo_id, cursor, now),
            )
            conn.commit()

    def list_queued(self, limit: int = 50) -> List[SyncEvent]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT event_id, source, kind, cursor, payload_json, occurred_at,
                       tenant_id, silo_id
                FROM sync_events
                WHERE status = 'queued'
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        events = []
        for row in rows:
            events.append(
                SyncEvent(
                    event_id=row[0],
                    source=row[1],
                    kind=row[2],
                    cursor=row[3],
                    payload=json.loads(row[4]),
                    occurred_at=row[5],
                    tenant_id=row[6],
                    silo_id=row[7],
                )
            )
        return events

    def mark_processed(self, event_id: str, cursor: Optional[str] = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE sync_events
                SET status = 'processed', updated_at = ?, last_error = NULL
                WHERE event_id = ?
                """,
                (now, event_id),
            )
            if cursor is not None:
                # Caller may also advance cursor separately; this is optional helper.
                pass
            conn.commit()

    def mark_failed(self, event_id: str, error: str, max_attempts: int = 5) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT attempts FROM sync_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            attempts = (row[0] if row else 0) + 1
            status = "failed" if attempts >= max_attempts else "queued"
            conn.execute(
                """
                UPDATE sync_events
                SET attempts = ?, status = ?, last_error = ?, updated_at = ?
                WHERE event_id = ?
                """,
                (attempts, status, error[:500], now, event_id),
            )
            conn.commit()

    def process_next(
        self,
        processor: Callable[[SyncEvent], None],
        max_attempts: int = 5,
    ) -> Optional[str]:
        """Process one queued event. Returns event_id if processed, None if queue empty."""
        queued = self.list_queued(limit=1)
        if not queued:
            return None
        event = queued[0]
        try:
            processor(event)
            self.mark_processed(event.event_id)
            if event.cursor:
                self.set_cursor(event.source, event.tenant_id, event.silo_id, event.cursor)
            return event.event_id
        except Exception as exc:
            self.mark_failed(event.event_id, str(exc), max_attempts=max_attempts)
            raise

    def health(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            queued = conn.execute(
                "SELECT COUNT(*) FROM sync_events WHERE status = 'queued'"
            ).fetchone()[0]
            failed = conn.execute(
                "SELECT COUNT(*) FROM sync_events WHERE status = 'failed'"
            ).fetchone()[0]
            processed = conn.execute(
                "SELECT COUNT(*) FROM sync_events WHERE status = 'processed'"
            ).fetchone()[0]
        return {
            "queued": queued,
            "failed": failed,
            "processed": processed,
            "db_path": self.db_path,
        }
