#!/usr/bin/env python3
"""Offline KnowledgeObject lineage + quality report. Does not import okc/."""

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


def report(payload: Dict[str, Any]) -> Dict[str, Any]:
    objects = _objects(payload)
    failed = []
    thin = 0
    for obj in objects:
        prov = obj.get("provenance") if isinstance(obj.get("provenance"), dict) else {}
        missing = []
        for key in REQUIRED:
            value = (prov or {}).get(key) or obj.get(key)
            if not value:
                missing.append(key)
        if missing:
            failed.append({"id": obj.get("id"), "missing": missing})
        content = str(obj.get("content") or "")
        if len(content.strip()) < 80:
            thin += 1
    return {
        "total": len(objects),
        "ok": len(objects) - len(failed),
        "failed": failed,
        "thin_content": thin,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Report KO lineage completeness.")
    parser.add_argument("path", help="Path to compiled package JSON")
    args = parser.parse_args()
    with open(args.path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    out = report(payload)
    print(json.dumps(out, indent=2))
    return 1 if out["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
