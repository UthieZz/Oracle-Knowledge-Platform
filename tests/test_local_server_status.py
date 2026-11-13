"""Regression for local OKC server job status API (P1/P3)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure repo root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from flask import Flask

# Import the app module under test
from okc.server import app as server_app


@pytest.fixture
def client():
    server_app.app.config["TESTING"] = True
    with server_app.app.test_client() as c:
        yield c
    # Clear jobs between tests
    with server_app._jobs_lock:
        server_app._jobs.clear()


def test_pipeline_status_exposes_strict_permissions(client):
    job_id = "job_test_strict"
    server_app._set_job(
        job_id,
        status="completed",
        progress=100,
        message="Completed: 2 objects (mode=strict)",
        strict_permissions=True,
    )
    resp = client.get(f"/api/pipeline/status?job_id={job_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["job_id"] == job_id
    assert data["status"] == "completed"
    assert data["strict_permissions"] is True
    assert "mode=strict" in data["message"]


def test_pipeline_status_omits_strict_permissions_when_absent(client):
    job_id = "job_test_pilot"
    server_app._set_job(
        job_id,
        status="completed",
        progress=100,
        message="Completed: 1 objects (mode=pilot)",
    )
    resp = client.get(f"/api/pipeline/status?job_id={job_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "strict_permissions" not in data
