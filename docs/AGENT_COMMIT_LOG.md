# AGENT_COMMIT_LOG

Living record of intentional agent commits on `main`.

**Rule:** Every successful intentional code/test/docs commit by an OKP agent MUST append one entry here in the same push (or the immediate follow-up push if the log was omitted). Newest entries at the top.

Do not invent commits. Record only verified SHAs after push verification.

Format per entry:

```
## YYYY-MM-DD — <short-sha>
- **Message:** <commit subject>
- **Files:** <paths>
- **Tests:** <what ran + result>
- **Why:** <one-line mechanism / roadmap link>
- **Next:** <single highest-leverage follow-up>
```

---

## 2026-10-12 — a3abd71
- **Message:** AGENT_COMMIT_LOG: stamp verified SHA a6e7399 for log introduction commit.
- **Files:** `docs/AGENT_COMMIT_LOG.md`
- **Tests:** none
- **Why:** Close the self-reference gap so the log only lists verified SHAs.
- **Next:** Persistent sync engine (cursor, durable queue, retry/idempotency) on top of Connect contract.

## 2026-10-12 — a6e7399
- **Message:** Add AGENT_COMMIT_LOG: living record updated on every intentional agent commit.
- **Files:** `docs/AGENT_COMMIT_LOG.md`, `docs/STAGE.md`
- **Tests:** none (docs-only convention)
- **Why:** Operators and daily agents need a single append-only evidence trail of what landed on main without reading full git history each session.
- **Next:** Implement persistent sync engine (cursor, durable queue, retry/idempotency) consuming `SyncEvent` into existing okc importer/compiler path.

## 2026-10-11 — df0a148
- **Message:** Add minimal OKP Connect contract: interfaces, SyncEvent, and contract test.
- **Files:** `okc/connect/__init__.py`, `okc/connect/interfaces.py`, `tests/test_connect_contract.py`, `docs/OKP_Connect_Contract.md`
- **Tests:** `test_connect_contract.py` + `test_okc_v2.py` + `test_plugin_registry.py` → 30 passed
- **Why:** Build-order step 1 — single connector contract (auth, initial/incremental sync, deletion, permissions, health) without touching Knowledge Core or creating a parallel IR.
- **Next:** Persistent sync engine before any real connector.
