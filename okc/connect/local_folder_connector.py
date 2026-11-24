"""Local folder connector for OKP Connect.

Polls a directory for .txt/.md files. Emits SyncEvents with file content or
deletion markers. Uses a persistent sequence number in the snapshot so that
event_ids remain stable for retries of the same logical change while allowing
legitimate delete/recreate of the same path and content to receive a new id.

Optional snapshot_path makes the change-detection map and sequence durable so
files deleted while the process is stopped are detected on the next incremental
sync after restart.

SyncWorker does not commit that snapshot until the resulting events are durably
enqueued. A pending journal (``<snapshot>.pending``) holds the staged snapshot
and events so a crash between detection and enqueue can be replayed. Direct
``initial_sync`` / ``incremental_sync`` callers still persist immediately.

A journal that already matches the committed snapshot is not a barrier. If
promoting the snapshot succeeds and deleting the journal fails, later scans
must still observe new source changes.
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
        self._last_snapshot: Dict[str, str] = {}
        self._seq: int = 0
        # Clean any leftover temp from prior interrupted persist
        if snapshot_path:
            tmp = Path(snapshot_path).with_suffix(Path(snapshot_path).suffix + ".tmp")
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
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

    def has_durable_snapshot(self) -> bool:
        """True if a prior change-detection snapshot was loaded or written.
        Used by SyncWorker to prefer incremental_sync after interruption
        even when the engine cursor has not yet advanced.
        """
        return bool(self._last_snapshot)

    def _persist_snapshot(self) -> None:
        if not self.snapshot_path:
            return
        path = Path(self.snapshot_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "seq": self._seq, "snapshot": self._last_snapshot}
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(path)  # atomic on POSIX
        except Exception:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            raise

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

    def _require_no_pending(self) -> None:
        if self.has_pending_journal():
            raise RuntimeError("pending snapshot journal must be committed before a new sync")

    def _pending_path(self) -> Optional[Path]:
        if not self.snapshot_path:
            return None
        p = Path(self.snapshot_path)
        return p.with_name(p.name + ".pending")

    def _read_json(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            return None
        return raw if isinstance(raw, dict) else None

    def _journal_matches_committed(self, journal: Dict[str, Any]) -> bool:
        """True when the durable snapshot already contains this journal.

        In-memory state is not consulted: stage_* advances memory before the
        snapshot file is promoted, and that must not look like a commit.
        """
        if not self.snapshot_path:
            return False
        committed = self._read_json(Path(self.snapshot_path))
        if not committed or "snapshot" not in committed or "seq" not in committed:
            return False
        try:
            same_seq = int(committed.get("seq") or 0) == int(journal.get("seq") or 0)
        except (TypeError, ValueError):
            return False
        return same_seq and committed.get("snapshot") == journal.get("snapshot")

    def has_pending_journal(self) -> bool:
        path = self._pending_path()
        if not path or not path.is_file():
            return False
        journal = self._read_json(path)
        if journal is not None and self._journal_matches_committed(journal):
            # Snapshot promotion already happened. A failed unlink must not
            # freeze change detection on this stale journal.
            try:
                path.unlink()
            except OSError:
                pass
            return False
        return True

    def _event_to_dict(self, ev: SyncEvent) -> Dict[str, Any]:
        return {
            "event_id": ev.event_id,
            "source": ev.source,
            "kind": ev.kind,
            "cursor": ev.cursor,
            "payload": ev.payload,
            "occurred_at": ev.occurred_at,
            "tenant_id": ev.tenant_id,
            "silo_id": ev.silo_id,
        }

    def _event_from_dict(self, item: Dict[str, Any]) -> SyncEvent:
        return SyncEvent(
            event_id=item["event_id"],
            source=item["source"],
            kind=item["kind"],
            cursor=item.get("cursor"),
            payload=item.get("payload") or {},
            occurred_at=item.get("occurred_at") or "",
            tenant_id=item.get("tenant_id") or "",
            silo_id=item.get("silo_id") or "",
        )

    def pending_events(self) -> List[SyncEvent]:
        path = self._pending_path()
        if path is None or not path.is_file():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("corrupt pending snapshot journal")
        return [self._event_from_dict(item) for item in (raw.get("events") or [])]

    def _write_journal(self, events: List[SyncEvent]) -> None:
        path = self._pending_path()
        if path is None:
            return
        payload = {
            "version": 1,
            "seq": self._seq,
            "snapshot": self._last_snapshot,
            "events": [self._event_to_dict(ev) for ev in events],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(path)
        except Exception:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            raise

    def commit_pending(self) -> None:
        """Promote a staged journal to the committed snapshot.

        Called only after the staged events have been durably enqueued.
        No journal is a no-op (direct sync methods already persist themselves).
        """
        path = self._pending_path()
        if path is None or not path.is_file():
            return
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or "snapshot" not in raw or "seq" not in raw:
            raise ValueError("corrupt pending snapshot journal")
        self._last_snapshot = raw.get("snapshot") or {}
        self._seq = int(raw.get("seq") or 0)
        self._persist_snapshot()
        try:
            path.unlink()
        except OSError:
            pass

    def _collect_initial(self, tenant_id: str, silo_id: str) -> List[SyncEvent]:
        snap = self._scan()
        events: List[SyncEvent] = []
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
        return events

    def _collect_incremental(self, tenant_id: str, silo_id: str) -> List[SyncEvent]:
        snap = self._scan()
        events: List[SyncEvent] = []
        prev = self._last_snapshot
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
        return events

    def initial_sync(self, tenant_id: str, silo_id: str) -> List[SyncEvent]:
        if not self._authenticated:
            raise RuntimeError("not authenticated")
        self._require_no_pending()
        old_seq = self._seq
        old_snapshot = dict(self._last_snapshot)
        try:
            events = self._collect_initial(tenant_id, silo_id)
            self._persist_snapshot()
            return events
        except Exception:
            self._seq = old_seq
            self._last_snapshot = old_snapshot
            raise

    def incremental_sync(self, cursor: str, tenant_id: str, silo_id: str) -> List[SyncEvent]:
        if not self._authenticated:
            raise RuntimeError("not authenticated")
        self._require_no_pending()
        old_seq = self._seq
        old_snapshot = dict(self._last_snapshot)
        try:
            events = self._collect_incremental(tenant_id, silo_id)
            self._persist_snapshot()
            return events
        except Exception:
            self._seq = old_seq
            self._last_snapshot = old_snapshot
            raise

    def stage_initial_sync(self, tenant_id: str, silo_id: str) -> List[SyncEvent]:
        """Stage an initial sync without advancing the committed snapshot.

        Events and the resulting snapshot are written to a pending journal.
        The committed snapshot is updated only by commit_pending(), after the
        caller has durably enqueued those events.
        """
        if not self._authenticated:
            raise RuntimeError("not authenticated")
        self._require_no_pending()
        old_seq = self._seq
        old_snapshot = dict(self._last_snapshot)
        try:
            events = self._collect_initial(tenant_id, silo_id)
            if events:
                self._write_journal(events)
            return events
        except Exception:
            self._seq = old_seq
            self._last_snapshot = old_snapshot
            raise

    def stage_incremental_sync(self, cursor: str, tenant_id: str, silo_id: str) -> List[SyncEvent]:
        """Stage an incremental sync without advancing the committed snapshot."""
        if not self._authenticated:
            raise RuntimeError("not authenticated")
        self._require_no_pending()
        old_seq = self._seq
        old_snapshot = dict(self._last_snapshot)
        try:
            events = self._collect_incremental(tenant_id, silo_id)
            if events:
                self._write_journal(events)
            return events
        except Exception:
            self._seq = old_seq
            self._last_snapshot = old_snapshot
            raise

    def handle_deletion(self, object_id: str, tenant_id: str, silo_id: str) -> SyncEvent:
        """Emit a delete event and keep durable snapshot consistent if the object is tracked.

        Advances sequence and, when the object is present in the current snapshot,
        removes it and persists so a subsequent restart or incremental_sync does not
        re-detect the deletion. On persist failure the in-memory state is restored.
        Caller is still expected to enqueue and process the returned event.
        """
        self._require_no_pending()
        old_seq = self._seq
        old_snapshot = dict(self._last_snapshot)
        try:
            event_id = self._make_event_id("delete", object_id)
            self._seq += 1
            if object_id in self._last_snapshot:
                del self._last_snapshot[object_id]
            self._persist_snapshot()
            return SyncEvent(
                event_id=event_id,
                source=self.name,
                kind="delete",
                payload={"object_id": object_id},
                tenant_id=tenant_id,
                silo_id=silo_id,
            )
        except Exception:
            self._seq = old_seq
            self._last_snapshot = old_snapshot
            raise

    def permissions(self, object_id: str) -> Dict[str, Any]:
        # Local folder has no per-object ACLs beyond OS; report open for demo.
        return {"read": True, "object_id": object_id, "source": self.name}

    def health(self) -> HealthStatus:
        if not self._authenticated:
            return HealthStatus.DEGRADED
        if not self.root.is_dir():
            return HealthStatus.FAILED
        return HealthStatus.OK
