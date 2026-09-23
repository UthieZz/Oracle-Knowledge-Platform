# OKP B2B Product Architecture

This document records constraints for preserving commercial optionality while OKP
is still an early-stage architecture.

## Product thesis

Commercial value should not depend on owning a particular LLM.

A customer should be able to connect an approved model or agent runtime while OKP
continues to provide the governed knowledge, provenance, retrieval, context, and
data-boundary layer.

This creates a replaceable model plane and a durable OKP plane.

## Deployment shapes

The architecture should support:

- local or desktop single-tenant deployments
- customer-controlled private deployments
- hosted multi-tenant SaaS
- hybrid deployments where sensitive knowledge remains customer-controlled

The same KnowledgePackage and Agent Context contracts should survive across these
deployment shapes.

## Commercial boundaries

Keep these concerns separable:

- core knowledge compiler and IR
- storage and retrieval adapters
- agent and context gateway
- enterprise identity and policy
- observability and audit
- billing and usage metering
- model-provider adapters

Do not couple the core IR to a single cloud vendor, model provider, vector database,
agent framework, or authentication provider.

## IP preservation

The repository should distinguish between:

- open interoperability contracts
- implementation details that may become proprietary
- customer-specific data and configuration

Do not place secrets, customer data, or deployment credentials in the repository.

Future licensing decisions should be made deliberately before distributing commercial
artifacts. This document does not select a license.

## Near-term engineering rule

Build interfaces before integrations.

The first useful agent integration should prove that:

1. a model can request context;
2. OKP can select and filter KnowledgeObjects;
3. provenance survives the boundary;
4. tenant and silo isolation is enforced;
5. the model can be swapped without changing the knowledge core.

After those invariants are demonstrated, MCP, OpenAI Agents SDK, local model runtimes,
or other agent frameworks can be added as adapters rather than becoming architectural
dependencies.
