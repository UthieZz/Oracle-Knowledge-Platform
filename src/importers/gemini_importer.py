"""Gemini Apps MyActivity JSON importer.

Reads Google Takeout exports from *My Activity > Gemini Apps* and maps
every activity record into the OKC :class:`~src.models.knowledge_package.KnowledgePackage`
IR using the same plugin contract as :class:`~src.importers.chatgpt_importer.ChatGPTImporter`.

Schema detected from live files (``gemini-myactivity-v1``):

.. code-block:: json

    [
      {
        "header": "Gemini Apps",
        "title": "Prompted <user text>",
        "time": "2026-05-22T22:32:28.471Z",
        "products": ["Gemini Apps"],
        "activityControls": ["Gemini Apps Activity"],
        "subtitles": [{"name": "Attached 2 files."}, {"name": "- f.png", "url": "f-hash.png"}],
        "imageFile": "filename-hash.png",
        "safeHtmlItem": [{"html": "<p>...</p>"}],
        "attachedFiles": ["filename-hash.png"]
      }
    ]

Design decisions
----------------
* **Conversation grouping** – records are sorted chronologically and split into
  synthetic conversations whenever the gap between two consecutive records
  exceeds *grouping_window* (default: 30 minutes).  The window is configurable.
* **Deterministic IDs** – each synthetic conversation gets a SHA-256 ID derived
  from its first record's timestamp + title, ensuring idempotent re-imports.
* **HTML → Markdown** – ``safeHtmlItem[].html`` is converted to lightweight
  Markdown (headings, bold, lists, code blocks, links) using the stdlib
  ``html.parser``.  No third-party library is required.
* **Provenance** – recorded on the :class:`~src.models.conversation.Conversation`
  object rather than on individual messages, keeping Message lightweight.
* **Import Manifest** – a summary dict is written to
  ``package.metadata["import_manifest"]`` after every run.
* **Progress callback** – optional ``Callable[[float, str], None]`` lets the UI
  report live progress without coupling the importer to Qt.
"""

from __future__ import annotations

import glob
import hashlib
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.core.interfaces import Importer
from src.models.conversation import Conversation
from src.models.knowledge_package import KnowledgePackage
from src.models.knowledge_object import KnowledgeObject
from src.models.message import Message

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------
_SCHEMA_V1 = "gemini-myactivity-v1"
_GEMINI_HEADER = "Gemini Apps"
_PROMPTED_PREFIX = "Prompted "

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class GeminiImportError(Exception):
    """Raised when a Gemini import cannot proceed due to a structural problem.

    Attributes:
        code: Short machine-readable error code (e.g. ``"malformed_json"``).
        message: Human-readable description.
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# Lightweight HTML → Markdown converter (stdlib only)
# ---------------------------------------------------------------------------


class _HtmlToMarkdown(HTMLParser):
    """Convert a subset of HTML to Markdown-like plain text.

    Supported elements: p, h1–h6, ul, ol, li, strong, b, em, i, code, pre, a, br, hr.
    Everything else has its tags stripped but text content is preserved.
    """

    def __init__(self):
        super().__init__()
        self._buf: List[str] = []
        self._in_pre = False
        self._in_li = False
        self._li_depth = 0
        self._ordered: List[int] = []  # stack of ordered-list counters

    # ------------------------------------------------------------------
    # HTMLParser overrides
    # ------------------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        attr_map = dict(attrs)
        t = tag.lower()
        if t in ("p",):
            self._newline(2)
        elif t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(t[1])
            self._newline(2)
            self._buf.append("#" * level + " ")
        elif t in ("ul",):
            self._newline(1)
            self._li_depth += 1
            self._ordered.append(0)
        elif t in ("ol",):
            self._newline(1)
            self._li_depth += 1
            self._ordered.append(1)
        elif t == "li":
            self._newline(1)
            indent = "  " * (self._li_depth - 1)
            if self._ordered and self._ordered[-1] > 0:
                self._ordered[-1] += 1
                self._buf.append(f"{indent}{self._ordered[-1]}. ")
            else:
                self._buf.append(f"{indent}- ")
        elif t in ("strong", "b"):
            self._buf.append("**")
        elif t in ("em", "i"):
            self._buf.append("*")
        elif t == "code" and not self._in_pre:
            self._buf.append("`")
        elif t == "pre":
            self._in_pre = True
            self._newline(1)
            self._buf.append("```\n")
        elif t == "a":
            href = attr_map.get("href", "")
            self._buf.append("[")
            self._buf.append(f"]({href})" if href else "")
        elif t == "br":
            self._buf.append("  \n")
        elif t == "hr":
            self._newline(1)
            self._buf.append("---")
            self._newline(1)

    def handle_endtag(self, tag: str):
        t = tag.lower()
        if t in ("p", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._newline(2)
        elif t in ("ul", "ol"):
            self._li_depth = max(0, self._li_depth - 1)
            if self._ordered:
                self._ordered.pop()
            self._newline(1)
        elif t == "li":
            pass  # trailing newline handled by next li/end-of-list
        elif t in ("strong", "b"):
            self._buf.append("**")
        elif t in ("em", "i"):
            self._buf.append("*")
        elif t == "code" and not self._in_pre:
            self._buf.append("`")
        elif t == "pre":
            self._in_pre = False
            self._buf.append("\n```")
            self._newline(2)
        elif t == "a":
            # We pre-inserted "](...)" in starttag so nothing more needed
            pass

    def handle_data(self, data: str):
        self._buf.append(data)

    def handle_entityref(self, name: str):  # HTML4 entities
        entities = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'", "nbsp": " ", "39": "'"}
        self._buf.append(entities.get(name, f"&{name};"))

    def handle_charref(self, name: str):  # &#NN; / &#xHH;
        try:
            if name.startswith("x"):
                ch = chr(int(name[1:], 16))
            else:
                ch = chr(int(name))
            self._buf.append(ch)
        except (ValueError, OverflowError):
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _newline(self, n: int = 1):
        text = "".join(self._buf)
        stripped = text.rstrip("\n")
        self._buf = [stripped, "\n" * n]

    def get_markdown(self) -> str:
        return "".join(self._buf).strip()


def _html_to_markdown(html: str) -> str:
    """Convert an HTML fragment to Markdown.  Returns empty string for empty input."""
    if not html or not html.strip():
        return ""
    parser = _HtmlToMarkdown()
    parser.feed(html)
    return parser.get_markdown()


# ---------------------------------------------------------------------------
# GeminiImporter
# ---------------------------------------------------------------------------


class GeminiImporter(Importer):
    """Production importer for Google Takeout Gemini Apps activity JSON.

    Plugin metadata
    ~~~~~~~~~~~~~~~
    Follows the identical interface contract as
    :class:`~src.importers.chatgpt_importer.ChatGPTImporter` so the
    :class:`~src.core.registry.PluginRegistry` can auto-discover and
    instantiate it without extra configuration.

    Parameters
    ----------
    input_dir:
        Directory (or single file path) to scan for ``*.json`` files.
    grouping_window_minutes:
        Maximum time gap (minutes) between consecutive activity records that
        are still considered part of the same synthetic conversation.
        Default: ``30``.
    progress_callback:
        Optional ``Callable[[float, str], None]``.  Receives a progress value
        in ``[0.0, 1.0]`` and a human-readable status string.  Called at key
        milestones during import so UI components can update a progress bar.
    """

    # ------------------------------------------------------------------
    # Plugin identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "Gemini Importer"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def author(self) -> str:
        return "OKC Core Team"

    @property
    def description(self) -> str:
        return (
            "Imports Google Takeout 'My Activity > Gemini Apps' JSON exports "
            "into the OKC KnowledgePackage IR.  Converts HTML responses to "
            "Markdown, groups records into synthetic conversations by temporal "
            "proximity, and attaches a full import manifest to the package."
        )

    @property
    def plugin_type(self) -> str:
        return "importer"

    @property
    def supported_inputs(self) -> List[str]:
        return ["application/json", "gemini-export", "gemini-myactivity-v1"]

    @property
    def supported_outputs(self) -> List[str]:
        return ["okc/conversations"]

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    def __init__(
        self,
        input_dir: str = "input",
        grouping_window_minutes: int = 30,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ):
        self.input_dir = input_dir
        self.grouping_window: timedelta = timedelta(minutes=grouping_window_minutes)
        self._progress_cb = progress_callback

        # Accumulated statistics (reset on each import_data call)
        self._reset_stats()

    # ------------------------------------------------------------------
    # Public API (Importer interface)
    # ------------------------------------------------------------------

    def import_data(self, package: KnowledgePackage) -> KnowledgePackage:
        """Entry point called by the pipeline / CLI.

        Discovers files, validates each payload, groups records into
        synthetic conversations, populates *package*, and writes an
        ``import_manifest`` to ``package.metadata``.

        Parameters
        ----------
        package:
            The :class:`~src.models.knowledge_package.KnowledgePackage` to
            populate.  Existing conversations are preserved.

        Returns
        -------
        KnowledgePackage
            The same *package* with new conversations appended.

        Raises
        ------
        GeminiImportError
            If *all* discovered files fail validation.  If only some files
            fail the errors are recorded in the import manifest and import
            continues with the remaining files.
        """
        self._reset_stats()
        self._progress(0.0, "Starting Gemini import…")

        files = self.discover_files()
        if not files:
            _LOG.warning("GeminiImporter: no files found in '%s'", self.input_dir)
            self._warnings.append(f"No JSON files found in '{self.input_dir}'.")

        for idx, fpath in enumerate(files):
            file_progress_start = 0.1 + (idx / max(len(files), 1)) * 0.8
            self._import_single_file(fpath, package, file_progress_start)

        self._progress(1.0, "Import complete.")
        self._attach_manifest(package, files)
        self._print_summary()
        return package

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_files(self) -> List[str]:
        """Return absolute paths of candidate JSON files.

        If *input_dir* is a file path that ends in ``.json`` it is returned
        directly.  Otherwise the directory is scanned for ``*.json``.
        """
        if os.path.isfile(self.input_dir) and self.input_dir.lower().endswith(".json"):
            return [os.path.abspath(self.input_dir)]

        pattern = os.path.join(self.input_dir, "*.json")
        return sorted(glob.glob(os.path.abspath(pattern)))

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_payload(self, data: Any, path: str) -> None:
        """Raise :class:`GeminiImportError` if *data* is structurally unusable."""
        if not isinstance(data, list):
            raise GeminiImportError(
                "unsupported_schema",
                f"Expected a JSON array in '{path}', got {type(data).__name__}.",
            )
        if len(data) == 0:
            raise GeminiImportError("empty_file", f"File '{path}' contains an empty array.")
        gemini_records = [r for r in data if isinstance(r, dict) and r.get("header") == _GEMINI_HEADER]
        if not gemini_records:
            raise GeminiImportError(
                "no_gemini_conversations",
                f"File '{path}' contains no records with header == '{_GEMINI_HEADER}'.",
            )

    # ------------------------------------------------------------------
    # Schema detection
    # ------------------------------------------------------------------

    def _detect_schema_version(self, data: List[Dict]) -> str:
        """Return a schema version string for provenance recording."""
        if data and isinstance(data[0], dict) and "safeHtmlItem" in data[0]:
            return _SCHEMA_V1
        return "gemini-myactivity-unknown"

    # ------------------------------------------------------------------
    # Core grouping logic
    # ------------------------------------------------------------------

    def _group_into_conversations(
        self,
        records: List[Dict],
        source_file: str,
        schema_version: str,
        imported_at: str,
    ) -> List[Conversation]:
        """Group a flat, chronologically sorted list of activity records into
        synthetic :class:`~src.models.conversation.Conversation` objects.

        A new conversation bucket is started whenever the gap between two
        consecutive records exceeds ``self.grouping_window``.
        """
        # Sort ascending by time so we can measure gaps
        def _parse_ts(r: Dict) -> datetime:
            ts = r.get("time", "")
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                return datetime(1970, 1, 1, tzinfo=timezone.utc)

        records = sorted(records, key=_parse_ts)

        conversations: List[Conversation] = []
        bucket: List[Dict] = []
        prev_dt: Optional[datetime] = None

        for rec in records:
            rec_dt = _parse_ts(rec)
            if prev_dt is not None and (rec_dt - prev_dt) > self.grouping_window:
                # Flush current bucket
                conv = self._bucket_to_conversation(bucket, source_file, schema_version, imported_at)
                if conv:
                    conversations.append(conv)
                bucket = []
            bucket.append(rec)
            prev_dt = rec_dt

        # Flush remaining
        if bucket:
            conv = self._bucket_to_conversation(bucket, source_file, schema_version, imported_at)
            if conv:
                conversations.append(conv)

        return conversations

    def _bucket_to_conversation(
        self,
        bucket: List[Dict],
        source_file: str,
        schema_version: str,
        imported_at: str,
    ) -> Optional[Conversation]:
        """Convert a list of temporally contiguous records into a Conversation."""
        if not bucket:
            return None

        messages: List[Message] = []
        attachments: List[Dict[str, Any]] = []

        for rec in bucket:
            user_msg, ai_msgs = self._parse_record_into_messages(rec)
            if user_msg:
                messages.append(user_msg)
            messages.extend(ai_msgs)
            attachments.extend(self._extract_attachments(rec))

        if not messages:
            return None

        first_rec = bucket[0]
        last_rec = bucket[-1]
        created = first_rec.get("time")
        updated = last_rec.get("time")
        title = self._derive_title(first_rec)
        conv_id = self._make_conversation_id(first_rec)

        provenance: Dict[str, Any] = {
            "source_platform": "Gemini",
            "source_file": source_file,
            "schema_version": schema_version,
            "imported_at": imported_at,
            "record_count": len(bucket),
            "attachment_count": len(attachments),
        }
        if attachments:
            provenance["attachments"] = attachments

        self._total_conversations += 1
        self._total_messages += len(messages)
        self._total_attachments += len(attachments)

        return Conversation(
            id=conv_id,
            title=title,
            source=source_file,
            created=created,
            updated=updated,
            messages=messages,
            provenance=provenance,
        )

    # ------------------------------------------------------------------
    # Record parsing
    # ------------------------------------------------------------------

    def _parse_record_into_messages(
        self, record: Dict
    ) -> Tuple[Optional[Message], List[Message]]:
        """Extract the user turn and AI response(s) from a single activity record.

        Returns
        -------
        Tuple[Optional[Message], List[Message]]
            ``(user_message_or_None, list_of_ai_messages)``
        """
        timestamp = record.get("time")

        # ── User message ──────────────────────────────────────────────
        raw_title: str = record.get("title", "")
        if raw_title.startswith(_PROMPTED_PREFIX):
            user_content = raw_title[len(_PROMPTED_PREFIX):].strip()
        else:
            user_content = raw_title.strip()

        user_msg: Optional[Message] = None
        if user_content:
            user_msg = Message(
                role="user",
                content=user_content,
                timestamp=timestamp,
            )

        # ── AI messages ───────────────────────────────────────────────
        ai_msgs: List[Message] = []
        for item in record.get("safeHtmlItem", []):
            html = item.get("html", "")
            md = _html_to_markdown(html)
            if md:
                ai_msgs.append(
                    Message(
                        role="assistant",
                        content=md,
                        timestamp=timestamp,
                    )
                )

        return user_msg, ai_msgs

    # ------------------------------------------------------------------
    # Attachments
    # ------------------------------------------------------------------

    def _extract_attachments(self, record: Dict) -> List[Dict[str, Any]]:
        """Return a list of attachment descriptor dicts from a record."""
        result: List[Dict[str, Any]] = []

        for sub in record.get("subtitles", []):
            name = sub.get("name", "")
            url = sub.get("url")
            # Skip the "Attached N files." string entry
            if name and not name.startswith("Attached ") and not name.startswith("-  "):
                result.append({"name": name, "url": url})
            elif name.startswith("-  "):
                # "- filename.png" style
                clean_name = name[3:].strip()
                result.append({"name": clean_name, "url": url})

        for fname in record.get("attachedFiles", []):
            if fname:
                result.append({"name": fname})

        # De-duplicate by name
        seen: set = set()
        deduped: List[Dict[str, Any]] = []
        for a in result:
            key = a.get("name", "")
            if key not in seen:
                seen.add(key)
                deduped.append(a)

        return deduped

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_conversation_id(self, first_record: Dict) -> str:
        """Generate a deterministic SHA-256 conversation ID."""
        key = (first_record.get("time", "") + first_record.get("title", "")).encode("utf-8")
        return "gemini-" + hashlib.sha256(key).hexdigest()[:16]

    def _derive_title(self, first_record: Dict) -> str:
        """Extract a clean, human-readable title from the first record."""
        raw = first_record.get("title", "Gemini Conversation")
        if raw.startswith(_PROMPTED_PREFIX):
            raw = raw[len(_PROMPTED_PREFIX):]
        return raw.strip() or "Gemini Conversation"

    def _progress(self, value: float, label: str) -> None:
        """Invoke the optional progress callback (silently ignored if absent)."""
        if self._progress_cb is not None:
            try:
                self._progress_cb(value, label)
            except Exception:
                pass  # Never let a UI callback crash the importer

    def _reset_stats(self) -> None:
        self._total_records: int = 0
        self._total_conversations: int = 0
        self._total_messages: int = 0
        self._total_attachments: int = 0
        self._warnings: List[str] = []
        self._errors: List[str] = []
        self._import_start: datetime = datetime.now(tz=timezone.utc)
        self._files_processed: int = 0
        self._schema_version: str = "unknown"

    def _import_single_file(
        self,
        fpath: str,
        package: KnowledgePackage,
        progress_start: float,
    ) -> None:
        """Load, validate, and parse a single JSON file into *package*."""
        import json

        self._progress(progress_start, f"Opening {os.path.basename(fpath)}…")
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                raw = fh.read()
        except OSError as exc:
            msg = f"Cannot read '{fpath}': {exc}"
            _LOG.error(msg)
            self._errors.append(msg)
            return

        self._progress(progress_start + 0.02, "Parsing JSON…")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            err = GeminiImportError("malformed_json", f"'{fpath}' is not valid JSON: {exc}")
            _LOG.error(err)
            self._errors.append(str(err))
            return

        try:
            self._validate_payload(data, fpath)
        except GeminiImportError as exc:
            _LOG.error(exc)
            self._errors.append(str(exc))
            return

        # Filter to Gemini records only
        gemini_records = [r for r in data if isinstance(r, dict) and r.get("header") == _GEMINI_HEADER]
        schema_version = self._detect_schema_version(gemini_records)
        self._schema_version = schema_version
        imported_at = self._import_start.isoformat()

        self._progress(progress_start + 0.05, f"Schema: {schema_version} — grouping {len(gemini_records)} records…")
        self._total_records += len(gemini_records)

        conversations = self._group_into_conversations(
            gemini_records, fpath, schema_version, imported_at
        )
        for conv in conversations:
            package.add_conversation(conv)
            package.add_knowledge_object(KnowledgeObject(
                id=conv.id,
                title=conv.title,
                content="\n\n".join([f"{msg.role}: {msg.content}" for msg in conv.messages]),
                source_platform=conv.provenance.get("source_platform", "Gemini"),
                source_file=conv.source,
                created_at=conv.created,
                updated_at=conv.updated,
                provenance=conv.provenance,
                evidence=[]
            ))

        self._files_processed += 1
        self._progress(
            progress_start + 0.08,
            f"Imported {len(conversations)} conversations from {os.path.basename(fpath)}",
        )

    def _attach_manifest(self, package: KnowledgePackage, files: List[str]) -> None:
        """Write an import manifest to ``package.metadata["import_manifest"]``."""
        duration = (datetime.now(tz=timezone.utc) - self._import_start).total_seconds()
        manifest: Dict[str, Any] = {
            "source": "gemini",
            "source_platform": "Gemini Apps",
            "schema_version": self._schema_version,
            "files_discovered": len(files),
            "files_processed": self._files_processed,
            "records_total": self._total_records,
            "conversations_created": self._total_conversations,
            "messages_created": self._total_messages,
            "attachments_found": self._total_attachments,
            "grouping_window_minutes": int(self.grouping_window.total_seconds() // 60),
            "import_duration_seconds": round(duration, 3),
            "imported_at": self._import_start.isoformat(),
            "warnings": self._warnings,
            "errors": self._errors,
        }
        package.update_metadata("import_manifest", manifest)

    def _print_summary(self) -> None:
        """Print a concise import summary to stdout (mirrors ChatGPTImporter style)."""
        print(f"[GeminiImporter] Files processed   : {self._files_processed}")
        print(f"[GeminiImporter] Records parsed    : {self._total_records}")
        print(f"[GeminiImporter] Conversations     : {self._total_conversations}")
        print(f"[GeminiImporter] Messages          : {self._total_messages}")
        print(f"[GeminiImporter] Attachments found : {self._total_attachments}")
        if self._warnings:
            for w in self._warnings:
                print(f"[GeminiImporter] WARN: {w}")
        if self._errors:
            for e in self._errors:
                print(f"[GeminiImporter] ERROR: {e}")
