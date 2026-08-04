"""Unit tests for GeminiImporter.

Run with:
    python -m pytest tests/test_gemini_importer.py -v

No third-party test dependencies beyond pytest are required.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from src.importers.gemini_importer import (
    GeminiImportError,
    GeminiImporter,
    _html_to_markdown,
)
from src.models.knowledge_package import KnowledgePackage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(data, suffix=".json") -> str:
    """Write *data* to a temp file and return its absolute path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


def _make_record(
    title: str = "Prompted Hello",
    time: str = "2026-01-01T12:00:00.000Z",
    html: str = "<p>Hi there!</p>",
    header: str = "Gemini Apps",
) -> dict:
    return {
        "header": header,
        "title": title,
        "time": time,
        "products": ["Gemini Apps"],
        "activityControls": ["Gemini Apps Activity"],
        "safeHtmlItem": [{"html": html}],
    }


def _importer_for_file(path: str, grouping_window_minutes: int = 30) -> GeminiImporter:
    return GeminiImporter(input_dir=path, grouping_window_minutes=grouping_window_minutes)


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestValidation:
    def test_malformed_json_raises(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as fh:
            fh.write("{this is not json")
        importer = _importer_for_file(path)
        pkg = KnowledgePackage()
        importer.import_data(pkg)  # Should not raise — error is captured in manifest
        manifest = pkg.metadata.get("import_manifest", {})
        assert any("not valid JSON" in e for e in manifest.get("errors", []))

    def test_non_list_root_raises(self):
        path = _write_json({"key": "value"})
        importer = _importer_for_file(path)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        manifest = pkg.metadata.get("import_manifest", {})
        assert any("unsupported_schema" in e or "JSON array" in e for e in manifest.get("errors", []))

    def test_empty_list_raises(self):
        path = _write_json([])
        importer = _importer_for_file(path)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        manifest = pkg.metadata.get("import_manifest", {})
        assert any("empty" in e.lower() for e in manifest.get("errors", []))

    def test_no_gemini_records_raises(self):
        path = _write_json([{"header": "YouTube", "title": "Watched video", "time": "2026-01-01T00:00:00Z"}])
        importer = _importer_for_file(path)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        manifest = pkg.metadata.get("import_manifest", {})
        assert any("no_gemini_conversations" in e or "Gemini Apps" in e for e in manifest.get("errors", []))

    def test_valid_file_produces_no_errors(self):
        path = _write_json([_make_record()])
        importer = _importer_for_file(path)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        manifest = pkg.metadata.get("import_manifest", {})
        assert manifest.get("errors", []) == []


# ---------------------------------------------------------------------------
# HTML → Markdown conversion tests
# ---------------------------------------------------------------------------


class TestHtmlToMarkdown:
    def test_plain_paragraph(self):
        result = _html_to_markdown("<p>Hello world</p>")
        assert "Hello world" in result

    def test_bold(self):
        result = _html_to_markdown("<p><strong>Bold</strong> text</p>")
        assert "**Bold**" in result

    def test_italic(self):
        result = _html_to_markdown("<em>Italic</em>")
        assert "*Italic*" in result

    def test_heading(self):
        result = _html_to_markdown("<h2>Section Title</h2>")
        assert "## Section Title" in result

    def test_unordered_list(self):
        result = _html_to_markdown("<ul><li>One</li><li>Two</li></ul>")
        assert "- One" in result
        assert "- Two" in result

    def test_ordered_list(self):
        result = _html_to_markdown("<ol><li>First</li><li>Second</li></ol>")
        assert "1. First" in result
        assert "2. Second" in result

    def test_code_inline(self):
        result = _html_to_markdown("<code>x = 1</code>")
        assert "`x = 1`" in result

    def test_pre_block(self):
        result = _html_to_markdown("<pre>def foo():\n    pass</pre>")
        assert "```" in result
        assert "def foo()" in result

    def test_link(self):
        result = _html_to_markdown('<a href="https://example.com">Example</a>')
        assert "https://example.com" in result
        assert "Example" in result

    def test_html_entities(self):
        result = _html_to_markdown("<p>a &amp; b &lt; c &gt; d</p>")
        assert "a & b < c > d" in result

    def test_empty_input_returns_empty(self):
        assert _html_to_markdown("") == ""
        assert _html_to_markdown("   ") == ""

    def test_nested_bold_in_list(self):
        result = _html_to_markdown("<ul><li><strong>Key</strong>: value</li></ul>")
        assert "**Key**" in result


# ---------------------------------------------------------------------------
# Temporal grouping tests
# ---------------------------------------------------------------------------


class TestTemporalGrouping:
    def _make_records_with_gap(self, gap_minutes: int) -> List[dict]:
        base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        t1 = base.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        t2 = (base + timedelta(minutes=gap_minutes)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        return [
            _make_record(title="Prompted First", time=t1),
            _make_record(title="Prompted Second", time=t2),
        ]

    def test_records_within_window_same_conversation(self):
        """Records 20 min apart (< 30 min window) → one conversation."""
        path = _write_json(self._make_records_with_gap(20))
        importer = _importer_for_file(path, grouping_window_minutes=30)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        assert len(pkg.conversations) == 1

    def test_records_beyond_window_different_conversations(self):
        """Records 60 min apart (> 30 min window) → two conversations."""
        path = _write_json(self._make_records_with_gap(60))
        importer = _importer_for_file(path, grouping_window_minutes=30)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        assert len(pkg.conversations) == 2

    def test_records_exactly_at_window_boundary(self):
        """Records exactly 30 min apart are NOT split (gap must be strictly >)."""
        path = _write_json(self._make_records_with_gap(30))
        importer = _importer_for_file(path, grouping_window_minutes=30)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        assert len(pkg.conversations) == 1

    def test_custom_window_respected(self):
        """Using a 5-minute window should split records 10 min apart."""
        path = _write_json(self._make_records_with_gap(10))
        importer = _importer_for_file(path, grouping_window_minutes=5)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        assert len(pkg.conversations) == 2

    def test_many_records_correct_grouping(self):
        """Three records: first two close together, third far away → 2 conversations."""
        base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        records = [
            _make_record(title="Prompted A", time=(base).strftime("%Y-%m-%dT%H:%M:%S.000Z")),
            _make_record(title="Prompted B", time=(base + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S.000Z")),
            _make_record(title="Prompted C", time=(base + timedelta(minutes=120)).strftime("%Y-%m-%dT%H:%M:%S.000Z")),
        ]
        path = _write_json(records)
        importer = _importer_for_file(path, grouping_window_minutes=30)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        assert len(pkg.conversations) == 2


# ---------------------------------------------------------------------------
# Import pass integration tests
# ---------------------------------------------------------------------------


class TestImportPass:
    def test_user_message_strips_prompted_prefix(self):
        path = _write_json([_make_record(title="Prompted What is Python?")])
        importer = _importer_for_file(path)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        assert len(pkg.conversations) == 1
        user_msgs = [m for m in pkg.conversations[0].messages if m.role == "user"]
        assert user_msgs[0].content == "What is Python?"

    def test_assistant_message_converted_from_html(self):
        path = _write_json([_make_record(html="<p><strong>Python</strong> is great.</p>")])
        importer = _importer_for_file(path)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        ai_msgs = [m for m in pkg.conversations[0].messages if m.role == "assistant"]
        assert len(ai_msgs) == 1
        assert "**Python**" in ai_msgs[0].content

    def test_provenance_on_conversation(self):
        path = _write_json([_make_record()])
        importer = _importer_for_file(path)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        conv = pkg.conversations[0]
        assert conv.provenance.get("source_platform") == "Gemini"
        assert conv.provenance.get("schema_version") == "gemini-myactivity-v1"
        assert "imported_at" in conv.provenance

    def test_import_manifest_attached_to_package(self):
        path = _write_json([_make_record()])
        importer = _importer_for_file(path)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        manifest = pkg.metadata.get("import_manifest")
        assert manifest is not None
        assert manifest["conversations_created"] >= 1
        assert manifest["messages_created"] >= 1
        assert "import_duration_seconds" in manifest

    def test_deterministic_conversation_ids(self):
        """Importing the same file twice produces the same conversation IDs."""
        records = [_make_record()]
        path = _write_json(records)
        pkg1 = KnowledgePackage()
        _importer_for_file(path).import_data(pkg1)
        pkg2 = KnowledgePackage()
        _importer_for_file(path).import_data(pkg2)
        ids1 = {c.id for c in pkg1.conversations}
        ids2 = {c.id for c in pkg2.conversations}
        assert ids1 == ids2

    def test_attachment_extraction(self):
        record = _make_record()
        record["subtitles"] = [
            {"name": "Attached 2 files."},
            {"name": "-  photo.png", "url": "photo-hash.png"},
        ]
        record["attachedFiles"] = ["photo-hash.png"]
        path = _write_json([record])
        importer = _importer_for_file(path)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        conv = pkg.conversations[0]
        attachments = conv.provenance.get("attachments", [])
        # "photo.png" should appear (deduped)
        names = [a["name"] for a in attachments]
        assert "photo.png" in names

    def test_progress_callback_called(self):
        path = _write_json([_make_record()])
        calls: list[tuple[float, str]] = []
        importer = GeminiImporter(
            input_dir=path,
            grouping_window_minutes=30,
            progress_callback=lambda v, s: calls.append((v, s)),
        )
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        assert len(calls) >= 2
        # First call should be at 0.0, last at 1.0
        assert calls[0][0] == pytest.approx(0.0)
        assert calls[-1][0] == pytest.approx(1.0)

    def test_non_gemini_records_filtered_out(self):
        records = [
            _make_record(header="YouTube"),
            _make_record(header="Gemini Apps"),
        ]
        path = _write_json(records)
        importer = _importer_for_file(path)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        # Only the Gemini record should produce a conversation
        assert len(pkg.conversations) == 1

    def test_empty_user_title_still_produces_ai_message(self):
        record = _make_record(title="", html="<p>AI response only</p>")
        path = _write_json([record])
        importer = _importer_for_file(path)
        pkg = KnowledgePackage()
        importer.import_data(pkg)
        ai_msgs = [m for m in pkg.conversations[0].messages if m.role == "assistant"]
        assert len(ai_msgs) == 1
        assert "AI response only" in ai_msgs[0].content
