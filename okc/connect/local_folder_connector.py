"""Local folder connector for OKP Connect.

Polls a directory for .txt/.md files. Emits SyncEvents with file content or
deletion markers. Uses content hash + mtime for stable event_ids and cursor.
Never writes KnowledgePackage; feeds SyncEngine → existing importer path.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from okc.connect.interfaces import Connector, HealthStatus, SyncEvent


class LocalFolderConnector(Connector):
    """Replaceable local-folder source. Outbound-only, poll-based."""

    name = "local_folder"
    version = "0.1.0"

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self._authenticated = False
        self._last_snapshot: Dict[str, str] = {}  # rel_path -> content_hash

    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        # No credentials required for local path; verify readable.
        if not self.root.is_dir():
            return False
        self._authenticated = True
        return True

    def _scan(self) -> Dict[str, Dict[str, Any]]:
        """Return {rel_path: {text, hash, mtime}} for .txt/.md."""
        snapshot: Dict[str, Dict[str, Any]] = {}
        if not self.root.is_dir():
            return snapshot
        for p in self.root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in {".txt", ".md"}:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if not text.strip():
                continue
            rel = str(p.relative_to(self.root))
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            mtime = p.stat().st_mtime
            snapshot[rel] = {"text": text, "hash": content_hash, "mtime": mtime, "abs": str(p)}
        return snapshot

    def initial_sync(self, tenant_id: str, silo_id: str) -> List[SyncEvent]:
        if not self._authenticated:
            raise RuntimeError("not authenticated")
        snap = self._scan()
        events: List[SyncEvent] = []
        for rel, info in sorted(snap.items()):
            event_id = f"lf-{info['hash'][:16]}-{rel}"
            events.append(
                SyncEvent(
                    event_id=event_id,
                    source=self.name,
                    kind="create",
                    cursor=str(info["mtime"]),
                    payload={
                        "text": info["text"],
                        "object_id": rel,
                        "source_file": info["abs"],
                        "content_hash": info["hash"],
                    },
                    tenant_id=tenant_id,
                    silo_id=silo_id,
                )
            )
        self._last_snapshot = {rel: info["hash"] for rel, info in snap.items()}
        return events

    def incremental_sync(self, cursor: str, tenant_id: str, silo_id: str) -> List[SyncEvent]:
        if not self._authenticated:
            raise RuntimeError("not authenticated")
        snap = self._scan()
        events: List[SyncEvent] = []
        prev = self._last_snapshot
        # Creates / updates
        for rel, info in snap.items():
            if rel not in prev or prev[rel] != info["hash"]:
                kind = "update" if rel in prev else "create"
                event_id = f"lf-{info['hash'][:16]}-{rel}"
                events.append(
                    SyncEvent(
                        event_id=event_id,
                        source=self.name,
                        kind=kind,
                        cursor=str(info["mtime"]),
                        payload={
                            "text": info["text"],
                            "object_id": rel,
                            "source_file": info["abs"],
                            "content_hash": info["hash"],
                        },
                        tenant_id=tenant_id,
                        silo_id=silo_id,
                    )
                )
        # Deletes
        for rel in prev:
            if rel not in snap:
                event_id = f"lf-del-{hashlib.sha256(rel.encode()).hexdigest()[:16]}"
                events.append(
                    SyncEvent(
                        event_id=event_id,
                        source=self.name,
                        kind="delete",
                        payload={"object_id": rel},
                        tenant_id=tenant_id,
                        silo_id=silo_id,
                    )
                )
        self._last_snapshot = {rel: info["hash"] for rel, info in snap.items()}
        return events

    def handle_deletion(self, object_id: str, tenant_id: str, silo_id: str) -> SyncEvent:
        event_id = f"lf-del-{hashlib.sha256(object_id.encode()).hexdigest()[:16]}"
        return SyncEvent(
            event_id=event_id,
            source=self.name,
            kind="delete",
            payload={"object_id": object_id},
            tenant_id=tenant_id,
            silo_id=silo_id,
        )

    def permissions(self, object_id: str) -> Dict[str, Any]:
        # Local folder has no per-object ACLs beyond OS; report open for demo.
        return {"read": True, "object_id": object_id, "source": self.name}

    def health(self) -> HealthStatus:
        if not self._authenticated:
            return HealthStatus.DEGRADED
        if not self.root.is_dir():
            return HealthStatus.FAILED
        return HealthStatus.OK
