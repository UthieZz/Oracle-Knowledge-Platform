# Enterprise Tenant and Silo Architecture

## Data boundary

All operational data is tenant and business-silo scoped:

```text
tenants/{tenantId}/silos/{siloId}/
  meta/dashboard
  platforms/{platformId}
  conversations/{conversationId}
  conversations/{conversationId}/messages/{messageId}
  knowledgeObjects/{knowledgeObjectId}
  entities/{entityId}
  attachments/{attachmentId}
  sourceFingerprints/{contentFingerprint}
```

Source fingerprints are scoped to the silo. A source identity in one business silo must not reveal that the same material exists in another silo.

## Authentication and authorization

Firebase Authentication establishes the user identity. A trusted administrative service sets Firebase custom claims; the browser must never assign access claims.

Required claims:

```json
{
  "okp_admin": false,
  "okp_silos": ["acme/finance", "acme/legal"],
  "okp_access": [
    { "tenantId": "acme", "siloId": "finance", "role": "analyst" },
    { "tenantId": "acme", "siloId": "legal", "role": "viewer" }
  ]
}
```

Firestore rules allow reads only when the requested `tenantId/siloId` is in `okp_silos`, or the user is an `okp_admin`. Browser writes remain prohibited. The compiler runs with a trusted server identity and requires `OKP_TENANT_ID` and `OKP_SILO_ID` on every export.

## Required deployment sequence

1. Enable Firebase Authentication and choose enterprise identity providers, such as SAML, OIDC, or Microsoft Entra ID.
2. Create a trusted claim-management service using the Firebase Admin SDK.
3. Assign `okp_silos` only after the organisation's identity and entitlement review.
4. Migrate existing global Firestore records into the tenant/silo hierarchy.
5. Deploy the new Firestore rules before exposing the enterprise Studio.
6. Configure every compiler job with an explicit tenant and silo.
7. Scope semantic-search indexes, logs, storage paths, caches, and source-fingerprint registries to the same tenant and silo.

## Non-negotiable rule

The UI selector improves usability. Firestore rules and server-side search filters enforce security. Never rely on a frontend-selected tenant or silo as the authorization decision.
