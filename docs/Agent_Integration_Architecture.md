# OKP Agent Integration Architecture

Status: architectural foundation, 2026-09-23.

## Purpose

OKP remains the model-agnostic knowledge and provenance layer. An agent runtime or
LLM is a consumer of OKP, not the canonical owner of the knowledge system.

The integration boundary is the Agent Context Gateway.

    Sources
      ↓
    Importers
      ↓
    KnowledgePackage / IR
      ↓
    Analyzers / Compiler
      ↓
    Persistence + Retrieval
      ↓
    OKP Agent Context Gateway
      ↓
    Agent Runtime
      ↓
    Model

The reverse path is also supported for agent feedback, memory candidates, citations,
tool events, and audit records.

## Two different representations

KnowledgePackage is the canonical OKP intermediate representation.

AgentContextPackage is a filtered, model-facing representation.

AgentContextPackage must never become a second canonical knowledge store.

This separation lets OKP change its internal storage, retrieval engine, or compiler
without forcing every model integration to understand OKP internals.

## B2B design constraints

The agent boundary must be:

1. Tenant and silo aware.
2. Provenance preserving.
3. Model and provider agnostic.
4. Policy enforceable.
5. Auditable.
6. Explicit about capabilities and tools.
7. Compatible with local and hosted deployment.
8. Replaceable without changing the KnowledgePackage contract.

Agent identity and authorization are first-class concerns. An agent must not inherit
unrestricted access merely because a human has access.

Sensitive actions should be separately authorized and logged. Read-only knowledge
retrieval and state-changing tool execution are different trust classes.

## Standards strategy

OKP should not make MCP the internal canonical architecture.

MCP should be an optional interoperability adapter at the boundary. This preserves
OKP's proprietary value in knowledge compilation, provenance, governance, retrieval,
and context management while allowing compatible agent runtimes to interoperate.

Direct SDK, REST, local-process, and embedded-Python adapters may coexist.

## Agent request lifecycle

1. Agent submits an AgentContextRequest.
2. OKP authenticates the caller or trusts an already-authenticated local boundary.
3. OKP resolves tenant, silo, identity, purpose, and applicable policy.
4. Retrieval selects relevant KnowledgeObjects.
5. Policy filters the candidate set.
6. The Gateway converts approved objects into AgentContextPackage.
7. The agent runtime supplies that package to its model.
8. The agent may call tools or request additional context.
9. Outputs, tool events, memory candidates, and citations can be returned to OKP
   through a future feedback contract.
10. OKP records relevant audit and provenance events.

Context requests can therefore occur multiple times during one agent run.

## B2B product boundary

OKP Core:
- ingestion
- normalization
- KnowledgePackage
- provenance
- retrieval
- compilation
- storage abstraction

OKP Control Plane:
- tenants
- silos
- identity
- authorization
- policy
- audit
- usage metering
- configuration

OKP Agent Gateway:
- context requests
- model-facing context packages
- tool and capability exposure
- feedback
- interoperability adapters

Agent Runtime:
- planning
- model calls
- tool execution
- handoffs
- approvals

This commit intentionally adds only the boundary contract and a safe local gateway.
It does not prematurely implement enterprise RBAC, billing, hosted multi-tenancy,
or a specific agent framework.

## Security principles

External text is data, not authority.

Retrieved content must not silently become system instructions.

Memory is a governed data store, not an unconditional trust layer.

Tool access follows least privilege.

High-impact actions require deterministic policy checks and, where appropriate,
human approval.

Every context package should be traceable to its source KnowledgeObjects.
