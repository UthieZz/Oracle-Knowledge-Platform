"""Import Wizard view — production UI for importing Gemini conversation exports.

Replaces the earlier mock-only stub.  The view provides:

* A "Import Gemini Export…" button that opens a native file dialog.
* A configurable grouping-window spin-box (default: 30 minutes).
* A live progress bar driven by a Qt signal via :class:`ImportProgressReporter`.
* A read-only result summary panel showing conversation/message counts and any
  errors or warnings produced by the importer.
* The existing file-queue list so users can see previously imported files.

All business logic is delegated to ``controller.import_gemini_file()`` — this
view never touches ImportService or GeminiImporter directly.
"""

from __future__ import annotations

from typing import Any, Dict

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


# ---------------------------------------------------------------------------
# Background worker — keeps the UI responsive during long imports
# ---------------------------------------------------------------------------


class _ImportWorker(QObject):
    """Runs ``controller.import_gemini_file()`` on a background thread."""

    progress = Signal(float, str)   # (fraction 0–1, status string)
    finished = Signal(dict)         # import result dict
    error = Signal(str)             # unhandled exception message

    def __init__(self, controller, file_path: str, grouping_window: int):
        super().__init__()
        self._controller = controller
        self._file_path = file_path
        self._grouping_window = grouping_window

    @Slot()
    def run(self):
        try:
            result = self._controller.import_gemini_file(
                file_path=self._file_path,
                grouping_window_minutes=self._grouping_window,
                progress_callback=lambda v, s: self.progress.emit(v, s),
            )
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# ImportProgressReporter (thin QObject wrapper — kept for future reuse)
# ---------------------------------------------------------------------------


class ImportProgressReporter(QObject):
    """Wraps a Qt signal so it can be passed as a plain ``Callable``."""

    updated = Signal(float, str)

    def __call__(self, value: float, label: str) -> None:
        self.updated.emit(value, label)


# ---------------------------------------------------------------------------
# Main view widget
# ---------------------------------------------------------------------------


class ImportWizardView(QWidget):
    """Production Import Wizard — file selection, progress, and result summary."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self._thread: QThread | None = None
        self._worker: _ImportWorker | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout()
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # Title
        title = QLabel("Import Wizard")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        root.addWidget(title)

        subtitle = QLabel(
            "Import your Gemini conversation export (MyActivity.json) to begin compiling knowledge."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #888; margin-bottom: 4px;")
        root.addWidget(subtitle)

        # ── Action row ────────────────────────────────────────────────
        action_row = QHBoxLayout()

        self.import_btn = QPushButton("📂  Import Gemini Export…")
        self.import_btn.setToolTip("Select a Gemini MyActivity.json file to import.")
        self.import_btn.setMinimumHeight(36)
        self.import_btn.clicked.connect(self._on_import_gemini)
        action_row.addWidget(self.import_btn)

        action_row.addSpacing(16)

        grouping_label = QLabel("Grouping window:")
        grouping_label.setToolTip(
            "Maximum gap (minutes) between consecutive records that are still "
            "considered part of the same conversation."
        )
        action_row.addWidget(grouping_label)

        self.grouping_spin = QSpinBox()
        self.grouping_spin.setRange(1, 1440)
        self.grouping_spin.setValue(30)
        self.grouping_spin.setSuffix(" min")
        self.grouping_spin.setToolTip("Default: 30 minutes")
        self.grouping_spin.setFixedWidth(90)
        action_row.addWidget(self.grouping_spin)

        action_row.addStretch()
        root.addLayout(action_row)

        # ── Progress bar ──────────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Idle")
        self.progress_bar.setVisible(False)
        root.addWidget(self.progress_bar)

        # ── Result summary ────────────────────────────────────────────
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        root.addWidget(self.summary_label)

        self.detail_box = QTextEdit()
        self.detail_box.setReadOnly(True)
        self.detail_box.setMaximumHeight(120)
        self.detail_box.setStyleSheet(
            "background:#1e1e1e; color:#d4d4d4; font-family:monospace; font-size:11px;"
        )
        self.detail_box.setPlaceholderText("Import details will appear here…")
        root.addWidget(self.detail_box)

        # ── File queue list ───────────────────────────────────────────
        queue_label = QLabel("Imported files:")
        queue_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        root.addWidget(queue_label)

        self.file_list = QListWidget()
        root.addWidget(self.file_list)

        self.setLayout(root)

    # ------------------------------------------------------------------
    # Qt lifecycle
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_list()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_import_gemini(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Gemini MyActivity JSON",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return  # User cancelled

        self._start_import(path)

    def _start_import(self, file_path: str) -> None:
        """Spin up a background thread to run the import without blocking the UI."""
        self.import_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Starting…")
        self.summary_label.setText("")
        self.detail_box.clear()

        grouping_window = self.grouping_spin.value()

        self._thread = QThread(self)
        self._worker = _ImportWorker(self.controller, file_path, grouping_window)
        self._worker.moveToThread(self._thread)

        # Wire signals
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_import_finished)
        self._worker.error.connect(self._on_import_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    @Slot(float, str)
    def _on_progress(self, value: float, label: str) -> None:
        pct = int(value * 100)
        self.progress_bar.setValue(pct)
        self.progress_bar.setFormat(f"{pct}%  {label}")

    @Slot(dict)
    def _on_import_finished(self, result: Dict[str, Any]) -> None:
        self.import_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        status = result.get("status", "Unknown")
        convs = result.get("conversations", 0)
        msgs = result.get("messages", 0)
        schema = result.get("schema_version", "—")

        if status == "Done":
            self.progress_bar.setFormat("✔  Complete")
            self.summary_label.setText(
                f"<b style='color:#4caf50'>Import successful.</b>  "
                f"{convs} conversations · {msgs} messages · schema: {schema}"
            )
        else:
            self.progress_bar.setFormat("✖  Errors")
            self.summary_label.setText(
                f"<b style='color:#f44336'>Import finished with errors.</b>  "
                f"{convs} conversations · {msgs} messages"
            )

        lines: list[str] = []
        for w in result.get("warnings", []):
            lines.append(f"⚠  {w}")
        for e in result.get("errors", []):
            lines.append(f"✖  {e}")
        if not lines:
            lines.append("No warnings or errors.")
        self.detail_box.setPlainText("\n".join(lines))

        self.refresh_list()

    @Slot(str)
    def _on_import_error(self, message: str) -> None:
        self.import_btn.setEnabled(True)
        self.progress_bar.setFormat("✖  Failed")
        self.summary_label.setText(f"<b style='color:#f44336'>Unexpected error:</b> {message}")
        self.detail_box.setPlainText(message)
        QMessageBox.critical(self, "Import Failed", message)

    def refresh_list(self) -> None:
        self.file_list.clear()
        files = self.controller.import_service.get_imported_files()
        if not files:
            self.file_list.addItem("No files imported yet.  Use the button above to get started.")
            return
        for f in files:
            self.file_list.addItem(f"{f['path']}  —  {f['status']}")

