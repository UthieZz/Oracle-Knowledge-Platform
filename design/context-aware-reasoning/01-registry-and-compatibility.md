# Context Dimension Registry + Evidence Compatibility Rules

**Version:** 1.0  
**Status:** Locked  
**Date:** 2026-11-17

## A. Context Dimension Registry

### Ownership hierarchy (immutable)

| Layer | Authority | May do | May not do |
|-------|-----------|--------|------------|
| Global Registry | Canonical identifiers, core semantics, versioning | Define dimension_id, value_type, base sensitivity rules, resolution_policy | Domain-specific value lists beyond common ones |
| Domain Plugin | Extension within governed bounds | Add allowed values, refine sensitivity rules, declare domain resolution policies | Redefine dimension_id semantics or remove global constraints |
| KnowledgePackage | Declaration only | Advertise which dimensions it supports and which concrete values have evidence | Own, redefine, or alter dimension definitions |

### Key rules

- Package must not own a dimension definition. It declares support only.
- `can_be_assumed` permits a disclosed assumption. It does not establish evidence or make an assumed value equivalent to a resolved value.
- Dimension definitions are versioned. Changing a definition must not silently alter existing compiled knowledge.
- A dimension's possible values are not automatically evidence. The package must separately establish which values its sources support.
- LLM proposals remain provisional until validated against a registered dimension and evidence or domain rule.

### Value types

Enum (controlled_vocabulary), range, boolean, string, structured.

## B. Evidence Compatibility Rules

### Per-dimension classification (binding clarification)

Evidence classification is **per-dimension**, never global. A single span may be unconstrained for one dimension, fully compatible for another, and partially compatible for a third.

### Compatibility states

- `fully_compatible`
- `partially_compatible`
- `incompatible`
- `unconstrained`

Unconstrained evidence may be used as background. It cannot establish or substantiate a resolved dimension.

### Conflict handling (locked)

1. Detect conflict.
2. Check for applicable versioned domain rule.
3. If rule exists → apply it, record rationale, preserve conflicting evidence.
4. If no rule → retain conflict. Do not majority-vote. Do not silently prefer highest provenance. Disclose conflict. Offer both alternatives as affordances when well-supported.

### Affordance availability

| Condition | Availability |
|-----------|--------------|
| Evidence already present supporting target value | `available` (reuse) |
| No current evidence, but defined retrieval path exists | `retrievable` |
| No evidence and no retrieval path | `unsupported` → never emit |

### Assumption vs resolution

An assumption can never be promoted to resolved merely by repeated use or model acceptance. Promotion requires new supporting evidence or explicit user confirmation (`source: "user"`).
