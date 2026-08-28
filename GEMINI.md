# Oracle Knowledge Platform — Gemini CLI Project Context

## Purpose

Oracle Knowledge Platform (OKP) is a knowledge infrastructure system.

It transforms fragmented information from AI systems and other sources into reusable, searchable, traceable knowledge.

OKP is not primarily a chatbot and is not a conversation archive.

The core value is:

Many fragmented sources
→ fewer high-quality knowledge artifacts
→ reusable knowledge
→ grounded AI reasoning

## Core Architecture

The established architecture is:

Sources
→ Importers
→ KnowledgePackage
→ Analyzers / Compiler
→ Canonical Knowledge
→ Portable Exports + Firestore
→ Oracle Studio
→ Grounded AI interaction

Architectural ownership:

- KnowledgePackage / Compiler = canonical source of truth
- Firestore = operational / published representation
- Oracle Studio = application and interface
- Gemini = reasoning / generation layer

Do not reverse these responsibilities.

## Firebase-Native Direction (Hard Constraints)

- Firebase project: oracle-knowledge-platform
- Firebase Spark/no-cost plan is a HARD constraint.
- No Blaze.
- No billing.
- No Cloud Run.
- No paid Google Cloud infrastructure.
- No Vertex AI.
- No paid APIs/services.

The intended runtime architecture is:

Sources
→ OKC Importers
→ KnowledgePackage
→ Compiler
→ FirestoreExporter
→ Firestore
→ Oracle Studio (React/PWA)
→ Gemini

Do not recreate Flask as a permanent backend.

## Knowledge Principles

- Knowledge quality is more important than conversation volume.
- Preserve provenance and traceability.
- Preserve chronology and source relationships.
- Distinguish facts, decisions, proposals, hypotheses and inferences.
- Markdown is an export format, not the canonical knowledge model.
- Prefer deterministic processing whenever sufficient.
- Use AI where it materially improves knowledge quality.
- AI enriches knowledge; it does not replace traceability.

## Source of Truth Hierarchy

1. Current working repository = implementation truth.
2. Current deployed application = runtime truth.
3. Current test/terminal output = execution evidence.
4. GEMINI.md / OKP skill = persistent architectural context.
5. Uploaded project documents = historical evidence unless verified against the current repository.

## Current Development Phase

The project is in implementation, verification, stabilization and shipping mode.

Current Priority:

Browser
→ Oracle Studio Import
→ source file
→ existing importer
→ KnowledgePackage
→ existing compiler
→ Firestore
→ Studio refresh

## Quota-Efficient Agent Workflow

- Do not repeatedly rediscover architecture.
- Read project context before searching.
- Inspect only files necessary for the task.
- Prefer targeted searches.
- Do not repeatedly run expensive compilation.
- Do not repeat already-proven tests unnecessarily.
- Do not repeatedly retry failed API/quota operations.
- Separate investigation, implementation and verification.
- Stop when sufficient evidence has been obtained.
- Prefer deterministic local inspection over unnecessary AI reasoning.

## Grounded Chat

Grounded Chat should retrieve evidence before generation:

User question
→ retrieval
→ ranking
→ context construction
→ Gemini
→ answer
→ citation verification

The objective is trustworthy, evidence-backed answers.

If the knowledge base does not contain sufficient evidence, the system should be able to say so rather than inventing an answer.

## Architectural Guardrails

Do not:

- turn OKP into a generic chatbot
- make Markdown the canonical data model
- discard provenance
- put compiler business logic in React
- make Gemini the compiler
- spread Firestore business logic throughout unrelated layers
- recreate Flask as a permanent backend without an explicit requirement
- introduce infrastructure without measurable value
- redesign stable architecture without evidence
- build UI features before their underlying data contract exists
- claim production readiness without evidence

## Operating Principle

For every engineering decision, ask:

> How do we make fragmented information become trustworthy, reusable, searchable and traceable knowledge with the least unnecessary complexity?

Preserve the architecture.
Preserve provenance.
Prefer deterministic processing.
Use AI where it adds measurable value.
Work incrementally.
Verify before claiming.
Do not waste quota rediscovering what OKP already knows.
