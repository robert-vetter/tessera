# 0012. The SAP deployment path ships as documentation plus tested code seams

- **Status:** accepted
- **Date:** 2026-06-10

## Context

ROADMAP Phase 4 requires "a deployment path onto SAP AI Core / Generative AI
Hub for the models and SAP HANA Cloud for the graph/vector layer, with the
portable local mode preserved." Provisioning real cloud services is
project-shaping (external services/spend), so the maintainer was asked
(2026-06-10) and chose: **no provisioning this phase** — the deliverable is
the deployment *design*, executable as a runbook, plus working code seams so
opting in is configuration, not surgery. `docs/SAP_ALIGNMENT.md` explicitly
endorses this posture as the credible one ("designed to run on SAP AI Core
and HANA Cloud, with a portable local mode for development").

## Decision

- **`docs/DEPLOYMENT.md`** carries the component→service mapping, the full
  configuration reference, the provisioning runbook, and an explicit
  verified-vs-not-verified split.
- **`tessera/platform/`** is the only cloud-aware code: an env-derived
  `PlatformConfig` (default: `provider="none"`, the local mode) and a
  deliberately narrow `ModelProvider` protocol (`complete(system, prompt) →
  str`) with two adapters — **SAP Generative AI Hub on AI Core** (OAuth2
  client-credentials + deployment chat completions; the production target)
  and **Anthropic Messages** (the locally demoable fallback the maintainer
  chose). Pure stdlib HTTP, zero new dependencies; failures raise
  `ProviderError` so callers always fall back to deterministic rendering.
- **CI stays key-free.** Tests pin the request contracts and degradation
  rules against a fake transport; an end-to-end cloud call is documented as
  unverified until credentials exist.
- **No HANA persistence or vector seam yet.** The graph stays in-process
  (ADR 0004); the vector store arrives with embeddings, whose refreshed
  trigger ADR 0010 defines. Building a storage abstraction now would be
  dead code worn as deployment evidence — the overclaiming CLAUDE.md forbids.

## Consequences

- Anyone can audit exactly what a cloud opt-in changes: environment
  variables and one small module.
- A future provisioning session is an afternoon with the runbook, not a
  design effort; the narration surface (spec 0040) consumes the provider
  protocol without knowing which adapter is behind it.
- Accepted cost: the GenAI Hub adapter is contract-tested, not
  integration-tested. Stated in DEPLOYMENT.md; the shapes are version-named
  constants in one file.
- Accepted cost: maintaining an Anthropic adapter alongside the SAP target —
  justified by making the Joule-style demo real today, and it shares the
  protocol surface.

## Alternatives considered

- **Provision a BTP free-tier footprint now.** Declined by the maintainer:
  blocks an autonomous phase on interactive account setup and possible
  spend, for evidence the runbook + seams already make credible.
- **Use the official SDKs (`ai-core-sdk`, `anthropic`).** Rejected: the
  project has zero runtime dependencies by design (clone-and-run,
  reproducible CI); two small request shapes do not justify a dependency
  tree, and stdlib HTTP keeps the wire format visible and testable.
- **A generic LLM-gateway abstraction (LiteLLM-style).** Rejected: one
  narrow protocol with two explicit adapters is auditable; a gateway invites
  configuration sprawl and silent provider drift.
- **Mock-server integration tests (e.g. a local HTTP stub).** Rejected for
  now: the fake-transport tests pin the same contract without a test-only
  server dependency; a real integration test belongs to the provisioning
  session.
