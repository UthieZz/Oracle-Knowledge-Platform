# Exact next step for the operator

Code is on `main` at `UthieZz/Oracle-Knowledge-Platform`.

## Tenant / silo gate (required before Firestore export)

```bash
cd /path/to/Oracle-Knowledge-Platform
git pull origin main
cp .env.example .env
# set OKP_TENANT_ID, OKP_SILO_ID, GOOGLE_APPLICATION_CREDENTIALS
```

Assign claims (first admin):

```bash
pip install -r requirements.txt
python scripts/assign_okp_claims.py --uid YOUR_FIREBASE_UID \
  --tenant acme --silo default --role analyst --admin --dry-run
# remove --dry-run to apply
```

Full procedure: `docs/OPERATOR_TENANT_SILO_SETUP.md`

## Studio identity

Set `VITE_OKP_AUTH_PROVIDER` in Studio env to your Firebase OIDC/SAML provider ID.
Deploy `firestore.rules` before production reads.

## Confirm

```bash
test -f scripts/assign_okp_claims.py && echo CLAIMS_CLI_OK
test -f functions/index.js && echo CLAIMS_FN_OK
test -f docs/OPERATOR_TENANT_SILO_SETUP.md && echo SETUP_DOC_OK
grep -n OKP_TENANT_ID .env.example
```

## Local compile mode check (optional)

Start the local OKC server and confirm permission mode:

```bash
PYTHONPATH=. python -m okc.server.app
# in another shell
curl -s http://127.0.0.1:5000/api/health | python -m json.tool
# expect "strict_permissions": false (or true if OKP_STRICT_PERMISSIONS=1)
# also "upload_dir_writable": true and "db_parent_writable": true under normal local conditions
# "db_exists": true after first successful compile that persists to SQLite
# "upload_dir_absolute" and "db_path_absolute" show the resolved paths in use
# "process_id", "cwd_absolute", "upload_dir_configured", "sqlite_path_configured" provide process and path-config diagnostics
# "tenant_configured" and "silo_configured" true when OKP_TENANT_ID / OKP_SILO_ID are set
# "google_credentials_configured": true when GOOGLE_APPLICATION_CREDENTIALS is set
# "active_jobs_count": current in-memory jobs (0 when idle)
# "upload_dir_free_mb" and "db_parent_free_mb" show free space (MB) on the volumes holding uploads and the SQLite DB
# "process_start_time_utc" and "uptime_seconds" show process lifetime
```
