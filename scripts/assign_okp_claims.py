#!/usr/bin/env python3
"""Assign OKP tenant/silo custom claims with Firebase Admin SDK.

Trusted operators only. Never run from the browser.

Usage:
  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
  python scripts/assign_okp_claims.py \
    --uid USER_UID \
    --tenant acme \
    --silo finance \
    --role analyst

  # Multiple silos:
  python scripts/assign_okp_claims.py --uid USER_UID \
    --access acme/finance:analyst --access acme/legal:viewer

Claims written:
  okp_silos:  ["tenant/silo", ...]
  okp_access: [{tenantId, siloId, role}, ...]
  okp_admin:  false (use --admin to set true)
"""

from __future__ import annotations

import argparse
import json
import sys


def parse_access(raw: str) -> dict:
    # tenant/silo:role
    if ":" in raw:
        path, role = raw.split(":", 1)
    else:
        path, role = raw, "viewer"
    if "/" not in path:
        raise SystemExit(f"Invalid access '{raw}'; expected tenant/silo[:role]")
    tenant_id, silo_id = path.split("/", 1)
    return {"tenantId": tenant_id, "siloId": silo_id, "role": role}


def main() -> int:
    parser = argparse.ArgumentParser(description="Assign OKP Firebase custom claims")
    parser.add_argument("--uid", required=True, help="Firebase Auth user uid")
    parser.add_argument("--tenant", help="Single tenant id (with --silo)")
    parser.add_argument("--silo", help="Single silo id (with --tenant)")
    parser.add_argument("--role", default="analyst", help="Role for single silo")
    parser.add_argument(
        "--access",
        action="append",
        default=[],
        help="tenant/silo:role (repeatable)",
    )
    parser.add_argument("--admin", action="store_true", help="Set okp_admin=true")
    parser.add_argument("--dry-run", action="store_true", help="Print claims only")
    args = parser.parse_args()

    access = [parse_access(item) for item in args.access]
    if args.tenant and args.silo:
        access.append(
            {"tenantId": args.tenant, "siloId": args.silo, "role": args.role}
        )
    if not access and not args.admin:
        raise SystemExit("Provide --tenant/--silo or --access, or --admin")

    silos = sorted({f"{item['tenantId']}/{item['siloId']}" for item in access})
    claims = {
        "okp_admin": bool(args.admin),
        "okp_silos": silos,
        "okp_access": access,
    }
    print(json.dumps({"uid": args.uid, "claims": claims}, indent=2))

    if args.dry_run:
        return 0

    try:
        import firebase_admin
        from firebase_admin import auth, credentials
    except ImportError as exc:
        raise SystemExit(
            "firebase-admin is required. pip install firebase-admin"
        ) from exc

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.ApplicationDefault())

    auth.set_custom_user_claims(args.uid, claims)
    print(f"Claims assigned to uid={args.uid}. User must refresh ID token.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
