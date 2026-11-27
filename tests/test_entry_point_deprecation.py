"""Lock the surface-alignment deprecation warning on the legacy compiler entry.

run.py compiler mode must emit a clear warning directing operators to the
okc/ local pilot surfaces (server, verify_local_pilot, connect worker).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_compiler_mode_emits_deprecation_warning():
    result = subprocess.run(
        [sys.executable, "run.py", "compiler"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    # The legacy path may fail or succeed depending on inputs; we only require the warning.
    combined = result.stdout + result.stderr
    assert "WARNING: 'compiler' mode is the legacy src/ path" in combined
    assert "python run.py server" in combined
    assert "scripts/verify_local_pilot.py" in combined
    assert "scripts/run_connect_worker.py" in combined
    assert "docs/IMPLEMENTATION_OWNERSHIP.md" in combined
