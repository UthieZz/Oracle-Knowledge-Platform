from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


# Canonical pipeline stage definitions (order matters)
_PIPELINE_STAGES = [
    ("Import",                "Loads source data (Gemini / ChatGPT) → KnowledgePackage"),
    ("Attachment Processing", "Transforms image, audio, and PDF attachments into AttachmentKnowledge"),
    ("Discovery",             "Extracts entities, topics, and relationships"),
    ("Review",                "Deduplication, conflict resolution, quality checks"),
    ("Compilation",           "Assembles knowledge into structured output units"),
    ("Validation",            "Schema validation, completeness checks, linting"),
    ("Export",                "Renders output (Markdown, JSON, etc.) to target directory"),
]


class PipelineRunnerView(QWidget):
    """Pipeline Runner — launches the OKC compiler pipeline and streams progress.

    Displays the canonical pipeline stages in order and appends structured log
    lines to the terminal output panel as each stage executes.
    """

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout()
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(10)

        # Title
        title = QLabel("Pipeline Runner")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        root.addWidget(title)

        # Status + Run button row
        status_row = QHBoxLayout()
        self.status_label = QLabel("Status: Idle")
        self.status_label.setStyleSheet("font-size: 13px;")
        status_row.addWidget(self.status_label)
        status_row.addStretch()

        self.run_btn = QPushButton("▶  Run Pipeline")
        self.run_btn.setMinimumHeight(34)
        self.run_btn.clicked.connect(self._on_run)
        status_row.addWidget(self.run_btn)
        root.addLayout(status_row)

        # Stage overview panel
        stages_label = QLabel("Pipeline stages:")
        stages_label.setStyleSheet("font-weight: bold; margin-top: 6px;")
        root.addWidget(stages_label)

        stages_panel = QWidget()
        stages_layout = QVBoxLayout(stages_panel)
        stages_layout.setContentsMargins(8, 4, 8, 4)
        stages_layout.setSpacing(2)
        stages_panel.setStyleSheet(
            "background: #1a1a2e; border: 1px solid #333; border-radius: 6px;"
        )

        self._stage_labels: list[QLabel] = []
        for i, (stage, description) in enumerate(_PIPELINE_STAGES, start=1):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 1, 4, 1)

            num_lbl = QLabel(f"{i}.")
            num_lbl.setFixedWidth(20)
            num_lbl.setStyleSheet("color: #888; font-family: monospace;")
            row_layout.addWidget(num_lbl)

            stage_lbl = QLabel(f"<b>{stage}</b>")
            stage_lbl.setFixedWidth(120)
            stage_lbl.setStyleSheet("color: #a0c4ff;")
            row_layout.addWidget(stage_lbl)

            desc_lbl = QLabel(description)
            desc_lbl.setStyleSheet("color: #ccc; font-size: 11px;")
            desc_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            row_layout.addWidget(desc_lbl)

            status_dot = QLabel("○")
            status_dot.setFixedWidth(20)
            status_dot.setStyleSheet("color: #555;")
            self._stage_labels.append(status_dot)
            row_layout.addWidget(status_dot)

            stages_layout.addWidget(row_widget)

        root.addWidget(stages_panel)

        # Terminal output
        terminal_label = QLabel("Log output:")
        terminal_label.setStyleSheet("font-weight: bold; margin-top: 6px;")
        root.addWidget(terminal_label)

        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; font-family: monospace; font-size: 12px;"
        )
        self.terminal.setPlainText("Waiting to start…")
        root.addWidget(self.terminal)

        self.setLayout(root)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_run(self) -> None:
        self.run_btn.setEnabled(False)
        self.terminal.clear()
        self._reset_stage_dots()

        res = self.controller.pipeline_service.run_pipeline()
        status = res.get("status", "Unknown")
        self.status_label.setText(f"Status: {status}")

        self._log("Pipeline execution started.")
        for i, (stage, _) in enumerate(_PIPELINE_STAGES):
            self._log(f"  [{i + 1}/{len(_PIPELINE_STAGES)}] {stage} pass…")
            self._set_stage_dot(i, running=True)

        self._log("Pipeline finished.")
        for i in range(len(_PIPELINE_STAGES)):
            self._set_stage_dot(i, done=True)

        self.run_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log(self, text: str) -> None:
        self.terminal.append(f">>> {text}")

    def _reset_stage_dots(self) -> None:
        for lbl in self._stage_labels:
            lbl.setText("○")
            lbl.setStyleSheet("color: #555;")

    def _set_stage_dot(self, index: int, *, running: bool = False, done: bool = False) -> None:
        if index >= len(self._stage_labels):
            return
        lbl = self._stage_labels[index]
        if done:
            lbl.setText("●")
            lbl.setStyleSheet("color: #4caf50;")
        elif running:
            lbl.setText("◉")
            lbl.setStyleSheet("color: #ffb300;")
        else:
            lbl.setText("○")
            lbl.setStyleSheet("color: #555;")

