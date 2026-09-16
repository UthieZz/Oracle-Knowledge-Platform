#!/usr/bin/env python3
"""Offline KnowledgeObject provenance gate. Does not import or edit okc/."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

REQUIRED = ("source_platform", "source_file", "conversation_id")


def _objects(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if isinstance(payload.get("knowledge_objects"), list):
        return payload["knowledge_objects"]
    if isinstance(payload.get("objects"), list):
        return payload["objects"]
    return []


def _provenance(obj: Dict[str, Any]) -> Dict[str, Any]:
    raw = obj.get("provenance") or {}
    if not isinstance(raw, dict):
        return {}
    return raw


def check(payload: Dict[str, Any]) -> Dict[str, Any]:
    failed = []
    objects = _objects(payload)
    for obj in objects:
        prov = _provenance(obj)
        missing = []
        for key in REQUIRED:
            value = prov.get(key) or obj.get(key)
            if not value:
                missing.append(key)
        if missing:
            failed.append({"id": obj.get("id") or obj.get("object_id"), "missing": missing})
    return {
        "total": len(objects),
        "ok": len(objects) - len(failed),
        "failed": failed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate KnowledgeObject provenance in a package JSON.")
    parser.add_argument("path", help="Path to compiled package JSON")
    args = parser.parse_args()
    with open(args.path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    report = check(payload)
    print(json.dumps(report, indent=2))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
