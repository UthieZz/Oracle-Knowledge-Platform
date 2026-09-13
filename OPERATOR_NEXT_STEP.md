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
