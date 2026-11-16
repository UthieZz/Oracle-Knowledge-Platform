"""
Flask REST server for local OKC v2 ingestion and compilation.

Endpoints expected by studio/src/services/apiService.ts:
  POST /api/import/upload
  POST /api/compile
  GET  /api/pipeline/status?job_id=...

Run:
  PYTHONPATH=. python -m okc.server.app
"""

from __future__ import annotations

import os
import shutil
import sys
import threading
import time
import resource
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

from okc.compiler.passes.attachment_processing_pass import AttachmentProcessingPass
from okc.plugins import PluginRegistryError, default_okc_registry
from okc.search.hybrid_rag import HybridRAGEngine

UPLOAD_DIR = Path(os.environ.get("OKC_UPLOAD_DIR", "uploads/okc"))
DB_PATH = os.environ.get("OKC_SQLITE_PATH", "okp_local.db")
ALLOWED_EXT = {".json", ".pdf", ".png", ".jpg", ".jpeg", ".mp3", ".wav", ".txt", ".md"}
API_VERSION = "0.2.10-local"  # Diagnostic version for local pilot operators (P3)

# Process lifetime diagnostics (P3)
_PROCESS_START_TIME = time.time()

app = Flask(__name__)
CORS(app)

# In-memory job registry (process-local; fine for single-user local mode)
_jobs: Dict[str, Dict[str, Any]] = {}
_jobs_lock = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_job(job_id: str, **fields: Any) -> None:
    with _jobs_lock:
        job = _jobs.setdefault(job_id, {})
        job.update(fields)
        job["updated_at"] = _utc_now()


def _get_job(job_id: str) -> Dict[str, Any] | None:
    with _jobs_lock:
        return dict(_jobs.get(job_id) or {}) or None


def _run_pipeline(job_id: str) -> None:
    job = _get_job(job_id) or {}
    file_path = job.get("file_path")
    tenant_id = job.get("tenant_id")
    silo_id = job.get("silo_id")
    if not file_path:
        _set_job(job_id, status="failed", progress=100, message="missing file_path")
        return

    try:
        registry = default_okc_registry()
        _set_job(job_id, status="running", progress=10, message="Importing source into v2 IR")
        importer_spec = registry.importer_for(file_path)
        if importer_spec is None:
            suffix = Path(file_path).suffix.lower() or "(no extension)"
            raise PluginRegistryError(
                f"No importer registered for {suffix}. "
                "Supported source imports: .json conversation export, .txt, .md. "
                "PDF, image, and audio stay attachment processors and are not package importers."
            )
        package = importer_spec.plugin.process(file_path, tenant_id=tenant_id, silo_id=silo_id)

        _set_job(job_id, status="running", progress=35, message="Attachment processing")
        package = AttachmentProcessingPass(registry=registry).execute(package)

        _set_job(job_id, status="running", progress=55, message="Entity extraction")
        analyzer = registry.get("analyzer", "entity_extractor").plugin
        package = analyzer.run(package)

        _set_job(job_id, status="running", progress=65, message="Structural compilation")
        compiler = registry.get("compiler", "package_compiler").plugin
        package = compiler.compile(package)

        _set_job(job_id, status="running", progress=75, message="Hybrid RAG indexing")
        rag = HybridRAGEngine()
        strict = os.environ.get("OKP_STRICT_PERMISSIONS", "").lower() in ("1", "true", "yes")
        rag.index_package(package, strict_permissions=strict)

        _set_job(job_id, status="running", progress=90, message="Persisting to SQLite")
        exporter_cls = registry.get("exporter", "sqlite_exporter").plugin
        exporter_cls(db_path=DB_PATH).export(package, tenant_id=tenant_id, silo_id=silo_id, strict_permissions=strict)

        mode = "strict" if strict else "pilot"
        _set_job(
            job_id,
            status="completed",
            progress=100,
            message=f"Completed: {len(package.objects)} objects (mode={mode})",
            object_count=len(package.objects),
            package_id=package.package_id,
            strict_permissions=strict,
        )
    except Exception as exc:
        _set_job(
            job_id,
            status="failed",
            progress=100,
            message=str(exc),
            error=traceback.format_exc(),
        )


@app.post("/api/import/upload")
def import_upload():
    if "file" not in request.files:
        return jsonify({"error": "file field required"}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "empty filename"}), 400

    tenant_id = request.form.get("tenant_id") or os.environ.get("OKP_TENANT_ID") or "tenant_default"
    silo_id = request.form.get("silo_id") or os.environ.get("OKP_SILO_ID") or "silo_default"

    filename = secure_filename(file.filename)
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"unsupported extension: {ext}"}), 400

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    dest = UPLOAD_DIR / f"{job_id}_{filename}"
    file.save(dest)

    _set_job(
        job_id,
        job_id=job_id,
        status="idle",
        progress=0,
        message="Uploaded; awaiting compile",
        file_path=str(dest),
        tenant_id=tenant_id,
        silo_id=silo_id,
        created_at=_utc_now(),
    )
    return jsonify({"job_id": job_id, "status": "idle", "message": "uploaded"})


@app.post("/api/compile")
def compile_job():
    body = request.get_json(silent=True) or {}
    job_id = body.get("job_id")
    if not job_id:
        return jsonify({"error": "job_id required"}), 400

    job = _get_job(job_id)
    if not job:
        return jsonify({"error": f"unknown job_id: {job_id}"}), 404

    if job.get("status") == "running":
        return jsonify({"job_id": job_id, "status": "running"})

    # Allow tenant/silo override at compile time
    tenant_id = body.get("tenant_id") or job.get("tenant_id")
    silo_id = body.get("silo_id") or job.get("silo_id")
    _set_job(job_id, tenant_id=tenant_id, silo_id=silo_id, status="running", progress=5, message="Queued")

    thread = threading.Thread(target=_run_pipeline, args=(job_id,), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id, "status": "running"})


@app.get("/api/pipeline/status")
def pipeline_status():
    job_id = request.args.get("job_id")
    if not job_id:
        return jsonify({"error": "job_id required"}), 400
    job = _get_job(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404
    payload = {
        "job_id": job_id,
        "status": job.get("status", "idle"),
        "progress": int(job.get("progress") or 0),
        "message": job.get("message") or "",
    }
    if "strict_permissions" in job:
        payload["strict_permissions"] = bool(job["strict_permissions"])
    return jsonify(payload)


@app.get("/api/health")
def health():
    strict = os.environ.get("OKP_STRICT_PERMISSIONS", "").lower() in ("1", "true", "yes")
    # Basic readiness signals for local pilot operators (P3)
    upload_ready = False
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        test_file = UPLOAD_DIR / ".okp_health_write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        upload_ready = True
    except Exception:
        upload_ready = False

    db_parent = Path(DB_PATH).parent
    db_ready = False
    db_exists = False
    try:
        db_parent.mkdir(parents=True, exist_ok=True)
        db_ready = os.access(db_parent, os.W_OK)
        db_exists = Path(DB_PATH).is_file()
    except Exception:
        db_ready = False
        db_exists = False

    def _free_mb(path: Path) -> int | None:
        try:
            return shutil.disk_usage(path).free // (1024 * 1024)
        except Exception:
            return None

    payload = {
        "ok": True,
        "service": "okc-local-api",
        "strict_permissions": strict,
        "upload_dir_writable": upload_ready,
        "upload_dir_absolute": str(UPLOAD_DIR.resolve()),
        "upload_dir_free_mb": _free_mb(UPLOAD_DIR),
        "db_parent_writable": db_ready,
        "db_exists": db_exists,
        "db_path_absolute": str(Path(DB_PATH).resolve()),
        "db_parent_free_mb": _free_mb(db_parent),
        "tenant_configured": bool(os.environ.get("OKP_TENANT_ID", "").strip()),
        "silo_configured": bool(os.environ.get("OKP_SILO_ID", "").strip()),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": sys.platform,
        "api_version": API_VERSION,
        "listen_host": os.environ.get("OKC_API_HOST", "127.0.0.1"),
        "listen_port": int(os.environ.get("OKC_API_PORT", "5000")),
        "google_credentials_configured": bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()),
        "process_id": os.getpid(),
        "cwd_absolute": str(Path.cwd().resolve()),
        "process_start_time_utc": datetime.fromtimestamp(_PROCESS_START_TIME, timezone.utc).isoformat(),
        "uptime_seconds": int(time.time() - _PROCESS_START_TIME),
        "memory_rss_mb": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024),
        "active_threads_count": threading.active_count(),
        "cpu_count": os.cpu_count() or 0,
        "load_average": list(os.getloadavg()) if hasattr(os, "getloadavg") else None,
        "upload_dir_configured": bool(os.environ.get("OKC_UPLOAD_DIR", "").strip()),
        "sqlite_path_configured": bool(os.environ.get("OKC_SQLITE_PATH", "").strip()),
    }
    # Plugin registry readiness (P3 diagnostics under loadable components)
    try:
        reg = default_okc_registry()
        payload["registry_ready"] = True
        payload["registered_plugins_count"] = len(reg.list())
        importers = reg.list("importer")
        payload["registered_importers_count"] = len(importers)
        payload["registered_importer_names"] = sorted(s.name for s in importers)
    except Exception:
        payload["registry_ready"] = False
        payload["registered_plugins_count"] = 0
        payload["registered_importers_count"] = 0
        payload["registered_importer_names"] = []
    with _jobs_lock:
        payload["active_jobs_count"] = len(_jobs)
    return jsonify(payload)


def main() -> None:
    host = os.environ.get("OKC_API_HOST", "127.0.0.1")
    port = int(os.environ.get("OKC_API_PORT", "5000"))
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
