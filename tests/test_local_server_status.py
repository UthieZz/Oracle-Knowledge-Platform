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
    assert "db_exists" in data
    assert isinstance(data["db_exists"], bool)
    assert "python_version" in data
    assert "platform" in data
    assert "api_version" in data
    assert data["api_version"] == "0.2.4-local"
    assert "upload_dir_absolute" in data
    assert isinstance(data["upload_dir_absolute"], str) and data["upload_dir_absolute"]
    assert "upload_dir_free_mb" in data
    assert data["upload_dir_free_mb"] is None or (isinstance(data["upload_dir_free_mb"], int) and data["upload_dir_free_mb"] >= 0)
    assert "db_path_absolute" in data
    assert "db_parent_free_mb" in data
    assert data["db_parent_free_mb"] is None or (isinstance(data["db_parent_free_mb"], int) and data["db_parent_free_mb"] >= 0)
    assert isinstance(data["db_path_absolute"], str) and data["db_path_absolute"]
    assert "google_credentials_configured" in data
    assert isinstance(data["google_credentials_configured"], bool)
    assert "active_jobs_count" in data
    assert isinstance(data["active_jobs_count"], int)
    assert "process_id" in data
    assert isinstance(data["process_id"], int) and data["process_id"] > 0
    assert "cwd_absolute" in data
    assert isinstance(data["cwd_absolute"], str) and data["cwd_absolute"]
    assert "upload_dir_configured" in data
    assert isinstance(data["upload_dir_configured"], bool)
    assert "sqlite_path_configured" in data
    assert isinstance(data["sqlite_path_configured"], bool)
    assert "registry_ready" in data
    assert isinstance(data["registry_ready"], bool)
    assert "registered_plugins_count" in data
    assert isinstance(data["registered_plugins_count"], int) and data["registered_plugins_count"] >= 2
    assert "registered_importers_count" in data
    assert isinstance(data["registered_importers_count"], int) and data["registered_importers_count"] >= 1
    assert isinstance(data["python_version"], str)
    assert isinstance(data["platform"], str)
    assert "google_credentials_configured" in data
    assert isinstance(data["google_credentials_configured"], bool)
    assert "active_jobs_count" in data
    assert isinstance(data["active_jobs_count"], int)


def test_health_reports_pilot_by_default(client, monkeypatch):
    monkeypatch.delenv("OKP_STRICT_PERMISSIONS", raising=False)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["strict_permissions"] is False
    assert "upload_dir_writable" in data
    assert "db_parent_writable" in data
    assert "db_exists" in data
    assert isinstance(data["db_exists"], bool)
    assert "python_version" in data
    assert "platform" in data
    assert "api_version" in data
    assert data["api_version"] == "0.2.4-local"
    assert "upload_dir_absolute" in data
    assert isinstance(data["upload_dir_absolute"], str) and data["upload_dir_absolute"]
    assert "upload_dir_free_mb" in data
    assert data["upload_dir_free_mb"] is None or (isinstance(data["upload_dir_free_mb"], int) and data["upload_dir_free_mb"] >= 0)
    assert "db_path_absolute" in data
    assert "db_parent_free_mb" in data
    assert data["db_parent_free_mb"] is None or (isinstance(data["db_parent_free_mb"], int) and data["db_parent_free_mb"] >= 0)
    assert isinstance(data["db_path_absolute"], str) and data["db_path_absolute"]
    assert "google_credentials_configured" in data
    assert isinstance(data["google_credentials_configured"], bool)
    assert "active_jobs_count" in data
    assert isinstance(data["active_jobs_count"], int)
    assert "registry_ready" in data
    assert isinstance(data["registry_ready"], bool)
    assert "registered_plugins_count" in data
    assert isinstance(data["registered_plugins_count"], int) and data["registered_plugins_count"] >= 2
    assert "registered_importers_count" in data
    assert isinstance(data["registered_importers_count"], int) and data["registered_importers_count"] >= 1


def test_health_reports_tenant_silo_configured(client, monkeypatch):
    monkeypatch.setenv("OKP_TENANT_ID", "acme")
    monkeypatch.setenv("OKP_SILO_ID", "default")
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["tenant_configured"] is True
    assert data["silo_configured"] is True
    assert "db_exists" in data
    assert isinstance(data["db_exists"], bool)
    assert "api_version" in data
    assert data["api_version"] == "0.2.4-local"
    assert "upload_dir_absolute" in data
    assert isinstance(data["upload_dir_absolute"], str) and data["upload_dir_absolute"]
    assert "upload_dir_free_mb" in data
    assert data["upload_dir_free_mb"] is None or (isinstance(data["upload_dir_free_mb"], int) and data["upload_dir_free_mb"] >= 0)
    assert "db_path_absolute" in data
    assert "db_parent_free_mb" in data
    assert data["db_parent_free_mb"] is None or (isinstance(data["db_parent_free_mb"], int) and data["db_parent_free_mb"] >= 0)
    assert isinstance(data["db_path_absolute"], str) and data["db_path_absolute"]
    assert "google_credentials_configured" in data
    assert isinstance(data["google_credentials_configured"], bool)
    assert "active_jobs_count" in data
    assert isinstance(data["active_jobs_count"], int)
    assert "python_version" in data
    assert "platform" in data


def test_health_reports_google_credentials_and_active_jobs(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/fake-sa.json")
    # Seed one job so count is non-zero
    server_app._set_job("job_health_count", status="idle")
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["google_credentials_configured"] is True
    assert data["active_jobs_count"] == 1
    # Clean up
    with server_app._jobs_lock:
        server_app._jobs.clear()


def test_health_reports_google_credentials_absent(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["google_credentials_configured"] is False
    assert data["active_jobs_count"] == 0
    monkeypatch.delenv("OKP_TENANT_ID", raising=False)
    monkeypatch.delenv("OKP_SILO_ID", raising=False)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["tenant_configured"] is False
    assert data["silo_configured"] is False
    assert "db_exists" in data
    assert isinstance(data["db_exists"], bool)
    assert "api_version" in data
    assert data["api_version"] == "0.2.4-local"
    assert "upload_dir_absolute" in data
    assert isinstance(data["upload_dir_absolute"], str) and data["upload_dir_absolute"]
    assert "upload_dir_free_mb" in data
    assert data["upload_dir_free_mb"] is None or (isinstance(data["upload_dir_free_mb"], int) and data["upload_dir_free_mb"] >= 0)
    assert "db_path_absolute" in data
    assert "db_parent_free_mb" in data
    assert data["db_parent_free_mb"] is None or (isinstance(data["db_parent_free_mb"], int) and data["db_parent_free_mb"] >= 0)
    assert isinstance(data["db_path_absolute"], str) and data["db_path_absolute"]
    assert "google_credentials_configured" in data
    assert isinstance(data["google_credentials_configured"], bool)
    assert "active_jobs_count" in data
    assert isinstance(data["active_jobs_count"], int)
    assert "python_version" in data
    assert "platform" in data
