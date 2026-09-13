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
import threading
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

from okc.analyzers.entity_extractor import EntityExtractor
from okc.compiler.passes.attachment_processing_pass import AttachmentProcessingPass
from okc.exporters.sqlite_exporter import SQLiteExporter
from okc.importers.json_importer import JsonToV2Importer
from okc.search.hybrid_rag import HybridRAGEngine

UPLOAD_DIR = Path(os.environ.get("OKC_UPLOAD_DIR", "uploads/okc"))
DB_PATH = os.environ.get("OKC_SQLITE_PATH", "okp_local.db")
ALLOWED_EXT = {".json", ".pdf", ".png", ".jpg", ".jpeg", ".mp3", ".wav", ".txt", ".md"}

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

    return jsonify(
        {
            "job_id": job_id,
            "file_path": str(dest),
            "tenant_id": tenant_id,
            "silo_id": silo_id,
            "message": "upload accepted",
        }
    )


def _run_pipeline(job_id: str) -> None:
    job = _get_job(job_id)
    if not job:
        return

    file_path = job["file_path"]
    tenant_id = job["tenant_id"]
    silo_id = job["silo_id"]

    try:
        _set_job(job_id, status="running", progress=10, message="Importing source into v2 IR")
        importer = JsonToV2Importer()
        package = importer.process(file_path, tenant_id=tenant_id, silo_id=silo_id)

        _set_job(job_id, status="running", progress=35, message="Attachment processing")
        package = AttachmentProcessingPass().execute(package)

        _set_job(job_id, status="running", progress=55, message="Entity extraction")
        package = EntityExtractor().run(package)

        _set_job(job_id, status="running", progress=75, message="Hybrid RAG indexing")
        rag = HybridRAGEngine()
        rag.index_package(package)

        _set_job(job_id, status="running", progress=90, message="Persisting to SQLite")
        SQLiteExporter(db_path=DB_PATH).export(package, tenant_id=tenant_id, silo_id=silo_id)

        _set_job(
            job_id,
            status="completed",
            progress=100,
            message=f"Completed: {len(package.objects)} objects",
            object_count=len(package.objects),
            package_id=package.package_id,
        )
    except Exception as exc:
        _set_job(
            job_id,
            status="failed",
            progress=100,
            message=str(exc),
            error=traceback.format_exc(),
        )


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
        return jsonify({"error": "job_id query param required"}), 400

    job = _get_job(job_id)
    if not job:
        return jsonify({"error": f"unknown job_id: {job_id}"}), 404

    return jsonify(
        {
            "job_id": job_id,
            "status": job.get("status", "idle"),
            "progress": int(job.get("progress") or 0),
            "message": job.get("message") or "",
        }
    )


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "okc-local-api"})


def main() -> None:
    host = os.environ.get("OKC_API_HOST", "127.0.0.1")
    port = int(os.environ.get("OKC_API_PORT", "5000"))
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
