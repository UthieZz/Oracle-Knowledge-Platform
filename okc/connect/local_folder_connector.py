"""Local folder connector for OKP Connect.

Polls a directory for .txt/.md files. Emits SyncEvents with file content or
deletion markers. Uses a persistent sequence number in the snapshot so that
event_ids remain stable for retries of the same logical change while allowing
legitimate delete/recreate of the same path and content to receive a new id.

Optional snapshot_path makes the change-detection map and sequence durable so
files deleted while the process is stopped are detected on the next incremental
sync after restart.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from okc.connect.interfaces import Connector, HealthStatus, SyncEvent


class LocalFolderConnector(Connector):
    """Replaceable local-folder source. Outbound-only, poll-based."""

    name = "local_folder"
    version = "0.1.2"

    def __init__(self, root: str, snapshot_path: Optional[str] = None) -> None:
        self.root = Path(root).resolve()
        self.snapshot_path = snapshot_path
        self._authenticated = False
        self._last_snapshot: Dict[str, str] = {}  # rel_path -> content_hash
        self._seq: int = 0
        if snapshot_path and Path(snapshot_path).exists():
            try:
                raw = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
                if isinstance(raw, dict) and "snapshot" in raw and "seq" in raw:
                    self._last_snapshot = raw.get("snapshot") or {}
                    self._seq = int(raw.get("seq") or 0)
                elif isinstance(raw, dict):
                    # Legacy flat {rel: hash} format
                    self._last_snapshot = raw
                    self._seq = 0
            except (json.JSONDecodeError, OSError, ValueError, TypeError):
                self._last_snapshot = {}
                self._seq = 0

    def _persist_snapshot(self) -> None:
        if not self.snapshot_path:
            return
        path = Path(self.snapshot_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "seq": self._seq, "snapshot": self._last_snapshot}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

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

    def _make_event_id(self, kind: str, rel: str, content_hash: Optional[str] = None) -> str:
        """Stable within one emission batch; sequence advances after persist."""
        base = f"lf-{self._seq}"
        if kind == "delete":
            return f"{base}-del-{hashlib.sha256(rel.encode()).hexdigest()[:12]}"
        h = (content_hash or "")[:12]
        return f"{base}-{h}-{rel}"

    def initial_sync(self, tenant_id: str, silo_id: str) -> List[SyncEvent]:
        if not self._authenticated:
            raise RuntimeError("not authenticated")
        snap = self._scan()
        events: List[SyncEvent] = []
        start_seq = self._seq
        for rel, info in sorted(snap.items()):
            event_id = self._make_event_id("create", rel, info["hash"])
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
            self._seq += 1
        self._last_snapshot = {rel: info["hash"] for rel, info in snap.items()}
        self._persist_snapshot()
        return events

    def incremental_sync(self, cursor: str, tenant_id: str, silo_id: str) -> List[SyncEvent]:
        if not self._authenticated:
            raise RuntimeError("not authenticated")
        snap = self._scan()
        events: List[SyncEvent] = []
        prev = self._last_snapshot
        # Creates / updates
        for rel, info in sorted(snap.items()):
            if rel not in prev or prev[rel] != info["hash"]:
                kind = "update" if rel in prev else "create"
                event_id = self._make_event_id(kind, rel, info["hash"])
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
                self._seq += 1
        # Deletes
        for rel in sorted(prev):
            if rel not in snap:
                event_id = self._make_event_id("delete", rel)
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
                self._seq += 1
        self._last_snapshot = {rel: info["hash"] for rel, info in snap.items()}
        self._persist_snapshot()
        return events

    def handle_deletion(self, object_id: str, tenant_id: str, silo_id: str) -> SyncEvent:
        event_id = self._make_event_id("delete", object_id)
        self._seq += 1
        # Note: does not update snapshot; caller normally uses incremental path.
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
