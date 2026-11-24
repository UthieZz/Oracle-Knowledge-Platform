"""Managed background SyncWorker for OKP Connect.

Polls a Connector, enqueues SyncEvents into the durable SyncEngine,
and drains the queue via a caller-supplied processor. State (queue, cursor)
survives process restart because it lives in SQLite.

When the connector can stage a snapshot journal (LocalFolderConnector),
the committed snapshot is promoted only after enqueue succeeds. A crash
between detection and enqueue is recovered by replaying the journal.

Does not write KnowledgePackage. Processor is expected to feed the
existing importer/compiler path.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional

from okc.connect.interfaces import Connector, SyncEvent
from okc.connect.sync_engine import SyncEngine

logger = logging.getLogger(__name__)


class SyncWorker:
    """Start/stop lifecycle around SyncEngine + Connector polling."""

    def __init__(
        self,
        engine: SyncEngine,
        connector: Connector,
        tenant_id: str,
        silo_id: str,
        processor: Callable[[SyncEvent], Any],
        poll_interval: float = 5.0,
    ) -> None:
        self.engine = engine
        self.connector = connector
        self.tenant_id = tenant_id
        self.silo_id = silo_id
        self.processor = processor
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="okp-sync-worker")
        self._thread.start()
        self._running = True
        logger.info("SyncWorker started for source=%s tenant=%s silo=%s", self.connector.name, self.tenant_id, self.silo_id)

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self._running = False
        logger.info("SyncWorker stopped")

    @property
    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._poll_and_drain()
            except Exception as exc:  # noqa: BLE001
                logger.exception("SyncWorker poll cycle failed: %s", exc)
            # Sleep in small slices so stop is responsive
            for _ in range(int(self.poll_interval * 10)):
                if self._stop.is_set():
                    break
                time.sleep(0.1)

    def _next_events(self) -> list:
        """Return the next batch, replaying a staged journal before scanning again."""
        connector = self.connector
        if getattr(connector, "has_pending_journal", lambda: False)():
            return connector.pending_events()
        cursor = self.engine.get_cursor(connector.name, self.tenant_id, self.silo_id)
        # Prefer connector durable snapshot when present so an interruption
        # between snapshot persist and cursor advance still detects later
        # deletions/changes instead of re-running a full initial_sync.
        prefer_incremental = cursor is not None
        if hasattr(connector, "has_durable_snapshot") and connector.has_durable_snapshot():
            prefer_incremental = True
        if prefer_incremental and hasattr(connector, "stage_incremental_sync"):
            return connector.stage_incremental_sync(cursor or "", self.tenant_id, self.silo_id)
        if not prefer_incremental and hasattr(connector, "stage_initial_sync"):
            return connector.stage_initial_sync(self.tenant_id, self.silo_id)
        if prefer_incremental:
            return connector.incremental_sync(cursor or "", self.tenant_id, self.silo_id)
        return connector.initial_sync(self.tenant_id, self.silo_id)

    def _poll_and_drain(self) -> None:
        if not getattr(self.connector, "_authenticated", True):
            # Best-effort; connectors may not expose the private flag
            pass
        events = self._next_events()
        for ev in events:
            self.engine.enqueue(ev)
        # Commit only after the batch is durable. No journal is a no-op.
        if getattr(self.connector, "has_pending_journal", lambda: False)():
            self.connector.commit_pending()
        # Drain queue
        while not self._stop.is_set():
            eid = self.engine.process_next(self.processor)
            if eid is None:
                break

    def health(self) -> dict:
        base = self.engine.health()
        base["worker_running"] = self.is_running
        base["connector_health"] = str(self.connector.health().value) if hasattr(self.connector, "health") else "unknown"
        return base
