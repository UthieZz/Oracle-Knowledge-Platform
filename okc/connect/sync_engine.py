"""Persistent SyncEngine for OKP Connect.

SQLite-backed durable queue with cursor tracking, idempotency by event_id,
and exponential retry backoff (next_retry_at). Feeds caller-supplied processor that uses existing
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

    def __init__(self, db_path: str, max_attempts: int = 5) -> None:
        self.db_path = db_path
        self.max_attempts = max_attempts
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
                    processed_at TEXT,
                    next_retry_at TEXT
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
            # Migrate existing tables that lack next_retry_at
            with self._conn() as conn:
                cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
                if "next_retry_at" not in cols:
                    conn.execute("ALTER TABLE events ADD COLUMN next_retry_at TEXT")
