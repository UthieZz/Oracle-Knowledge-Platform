"""Persistent SyncEngine for OKP Connect.

SQLite-backed durable queue with cursor tracking, idempotency by event_id,
and simple retry/backoff. Feeds caller-supplied processor that uses existing
importer/compiler path. Never writes KnowledgePackage directly.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from okc.connect.interfaces import SyncEvent


class SyncEngine:
    """Durable, idempotent sync queue and cursor store."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    cursor TEXT,
                    payload TEXT NOT NULL,
                    occurred_at TEXT,
                    tenant_id TEXT NOT NULL,
                    silo_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    enqueued_at TEXT NOT NULL,
                    processed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS cursors (
                    source TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    silo_id TEXT NOT NULL,
                    cursor TEXT,
                    updated_at TEXT,
                    PRIMARY KEY (source, tenant_id, silo_id)
                );
                CREATE INDEX IF NOT EXISTS idx_events_status ON events(status, enqueued_at);
                """
            )

    def enqueue(self, event: SyncEvent) -> bool:
        """Enqueue if not already present. Returns True if newly inserted."""
        payload_json = json.dumps(event.payload, default=str)
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO events
                (event_id, source, kind, cursor, payload, occurred_at, tenant_id, silo_id, status, enqueued_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?)
                """,
                (
                    event.event_id,
                    event.source,
                    event.kind,
                    event.cursor,
                    payload_json,
                    event.occurred_at,
                    event.tenant_id,
                    event.silo_id,
                    now,
                ),
            )
            return cur.rowcount > 0

    def process_next(self, processor: Callable[[SyncEvent], Any]) -> Optional[str]:
        """Process the oldest queued event. Returns event_id or None if empty.

        On processor exception, increments attempts and leaves status queued
        (simple retry). Marks processed only on success.
        """
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM events
                WHERE status = 'queued'
                ORDER BY enqueued_at ASC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None

            event = SyncEvent(
                event_id=row["event_id"],
                source=row["source"],
                kind=row["kind"],
                cursor=row["cursor"],
                payload=json.loads(row["payload"]),
                occurred_at=row["occurred_at"],
                tenant_id=row["tenant_id"],
                silo_id=row["silo_id"],
            )
            try:
                processor(event)
                now = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    """
                    UPDATE events
                    SET status = 'processed', processed_at = ?, attempts = attempts + 1
                    WHERE event_id = ?
                    """,
                    (now, event.event_id),
                )
                # Advance cursor if present
                if event.cursor:
                    conn.execute(
                        """
                        INSERT INTO cursors (source, tenant_id, silo_id, cursor, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(source, tenant_id, silo_id) DO UPDATE SET
                            cursor = excluded.cursor,
                            updated_at = excluded.updated_at
                        """,
                        (event.source, event.tenant_id, event.silo_id, event.cursor, now),
                    )
                return event.event_id
            except Exception as exc:  # noqa: BLE001
                conn.execute(
                    """
                    UPDATE events
                    SET attempts = attempts + 1, last_error = ?
                    WHERE event_id = ?
                    """,
                    (str(exc)[:500], event.event_id),
                )
                return None  # leave queued for retry

    def get_cursor(self, source: str, tenant_id: str, silo_id: str) -> Optional[str]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT cursor FROM cursors WHERE source = ? AND tenant_id = ? AND silo_id = ?",
                (source, tenant_id, silo_id),
            ).fetchone()
            return row["cursor"] if row else None

    def health(self) -> Dict[str, Any]:
        with self._conn() as conn:
            queued = conn.execute("SELECT COUNT(*) AS n FROM events WHERE status = 'queued'").fetchone()["n"]
            processed = conn.execute("SELECT COUNT(*) AS n FROM events WHERE status = 'processed'").fetchone()["n"]
            failed = conn.execute("SELECT COUNT(*) AS n FROM events WHERE attempts > 3 AND status = 'queued'").fetchone()["n"]
        return {
            "queued": queued,
            "processed": processed,
            "failed_or_stuck": failed,
            "db_path": self.db_path,
        }

    def list_queued(self) -> List[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT event_id FROM events WHERE status = 'queued' ORDER BY enqueued_at"
            ).fetchall()
            return [r["event_id"] for r in rows]
