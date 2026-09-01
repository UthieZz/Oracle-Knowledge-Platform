# OKP-Studio infusion plan

Captured 2026-09-01. This file is the contract for merging `UthieZz/OKP-Studio` into `UthieZz/Oracle-Knowledge-Platform` without breaking working code.

## Verified facts

| Surface | Location | Stack | Last push |
|---|---|---|---|
| Compiler / IR / exporters | this repo (`src/`, `run_*.py`) | Python | 2026-08-31 |
| Live Studio | this repo `studio/` | React 18, Vite 4, react-router-dom, Firebase, Tailwind 3 | 2026-08-31 (multi-model Ask) |
| Satellite Studio | `UthieZz/OKP-Studio` @ `1c862953` | React 19, Vite 8, TanStack Start/Router, PGlite/Postgres, better-auth, Vercel | 2026-08-27 |

`OKP-Studio` is **not** a drop-in replacement for `studio/`.
Different runtime, data store, auth, and router. A wholesale copy would break Firestore-backed Ask, Settings, and the Stage 2 publishing path.

## Locked architecture (do not invert)

```text
Sources → Importers → KnowledgePackage → Compiler → Exporters
                                              ├─ portable outputs
                                              └─ FirestoreExporter → Firestore → studio/ → Grounded Ask
```

- Compiler remains source of truth.
- Firestore remains operational store for beta Studio.
- `studio/` remains the consumer. It is not a second compiler.
- `OKP-Studio` may donate UI/auth *ideas* and isolated modules. It must not become the canonical knowledge store (PGlite is local app-builder state, not KnowledgePackage).

## What must never be copied into `studio/` as-is

- `package.json` / lockfile from OKP-Studio (React 19 + TanStack Start + PGlite + better-auth).
- `src/routeTree.gen.ts`, TanStack Start server routes.
- `server/`, `migrations/`, PGlite/Kysely schema.
- Vercel / Nitro runtime assumptions.
- Any path that writes canonical knowledge from the browser.

## What may be infused later (after Stage 3 runtime freeze)

Only after Grounded Ask is runtime-verified:

1. Isolated UI primitives (Radix-style controls, layout shells) rewritten against current `studio/src/components`.
2. Auth *pattern* notes from `better-auth` — Firebase Auth stays unless a measured beta need appears.
3. Attachment-viewer UX from `OKP-Studio/attachments` if it improves Stage 4 without changing exporter contracts.

Each candidate must answer: does this improve knowledge use without changing KnowledgePackage / Firestore contracts?

## Infusion method (safe)

Do **not** merge histories onto `studio/`.

Preferred sequence:

1. Keep `studio/` untouched on `main`.
2. Add a **reference remote** only (no subtree yet unless operator confirms).
3. If code is needed for comparison, vendor onto a branch:
   `vendor/okp-studio-reference/` via `git subtree` or sparse checkout.
4. Port file-by-file into `studio/src/` only when the contract is identical.
5. Delete nothing in live `studio/` until the replacement path is verified.

## Current stage

Roadmap Stage 3 code is on `main`. Runtime Ask is still unverified.
Infusion planning is Stage 3.5 documentation only. No runtime files changed in the commit that added this document.
