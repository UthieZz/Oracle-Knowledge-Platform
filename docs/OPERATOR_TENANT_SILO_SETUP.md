# Operator setup: tenant/silo env + claims

## 1. Compiler / export environment

```bash
cp .env.example .env
# edit:
# OKP_TENANT_ID=acme
# OKP_SILO_ID=default
# GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
```

Export refuses to run without tenant and silo:

```bash
python run_export.py
```

Writes under:

`tenants/{OKP_TENANT_ID}/silos/{OKP_SILO_ID}/...`

## 2. Bootstrap first admin claims (CLI)

Service account needs Firebase Auth Admin.

```bash
pip install firebase-admin
export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json

# dry-run
python scripts/assign_okp_claims.py --uid YOUR_FIREBASE_UID \
  --tenant acme --silo default --role analyst --admin --dry-run

# apply
python scripts/assign_okp_claims.py --uid YOUR_FIREBASE_UID \
  --tenant acme --silo default --role analyst --admin
```

User must sign out/in (or force token refresh) so claims appear on the ID token.

## 3. Cloud Function (ongoing assignment)

```bash
cd functions && npm install
firebase deploy --only functions:assignOkpClaims
```

Callable payload:

```json
{
  "uid": "target-user-uid",
  "access": [{ "tenantId": "acme", "siloId": "finance", "role": "analyst" }],
  "admin": false
}
```

Caller must already have `okp_admin: true`.

## 4. Studio

Set `VITE_OKP_AUTH_PROVIDER` to the Firebase Auth OIDC/SAML provider ID.
Deploy `firestore.rules` before exposing Studio against production data.

## Success signals

- `python run_export.py` fails fast if env missing.
- Export path includes `tenants/.../silos/...`.
- Signed-in user with claims can read silo data; unsigned / unassigned users cannot.
