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


def test_health_reports_strict_permissions(client, monkeypatch):
    monkeypatch.setenv("OKP_STRICT_PERMISSIONS", "1")
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["service"] == "okc-local-api"
    assert data["strict_permissions"] is True
    assert "upload_dir_writable" in data
    assert "db_parent_writable" in data
    assert isinstance(data["upload_dir_writable"], bool)
    assert isinstance(data["db_parent_writable"], bool)
    assert "python_version" in data
    assert "platform" in data
    assert isinstance(data["python_version"], str)
    assert isinstance(data["platform"], str)


def test_health_reports_pilot_by_default(client, monkeypatch):
    monkeypatch.delenv("OKP_STRICT_PERMISSIONS", raising=False)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["strict_permissions"] is False
    assert "upload_dir_writable" in data
    assert "db_parent_writable" in data
    assert "python_version" in data
    assert "platform" in data


def test_health_reports_tenant_silo_configured(client, monkeypatch):
    monkeypatch.setenv("OKP_TENANT_ID", "acme")
    monkeypatch.setenv("OKP_SILO_ID", "default")
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["tenant_configured"] is True
    assert data["silo_configured"] is True
    assert "python_version" in data
    assert "platform" in data


def test_health_reports_tenant_silo_absent_by_default(client, monkeypatch):
    monkeypatch.delenv("OKP_TENANT_ID", raising=False)
    monkeypatch.delenv("OKP_SILO_ID", raising=False)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["tenant_configured"] is False
    assert data["silo_configured"] is False
    assert "python_version" in data
    assert "platform" in data
