# 0039. The SAP deployment path: documentation + tested code seams, no provisioning

- **Phase / milestone:** Phase 4 — platform, polish, and the story (spec 0035 Unit 5)
- **Issue:** —
- **Status:** approved (maintainer decision recorded in spec 0035: docs + seams, no provisioning; ADR 0012 records the design)

## Problem

ROADMAP Phase 4 names a deployment path onto **SAP AI Core / Generative AI
Hub** (models) and **SAP HANA Cloud** (graph/vector), "with the portable local
mode preserved for development." The maintainer decided (asked, 2026-06-10):
no cloud service is provisioned this phase — the deliverable is the honest
"designed to run on SAP, portable local mode" posture `docs/SAP_ALIGNMENT.md`
endorses, made concrete: a deployment document a stranger could follow to
stand the stack up, plus real, tested code seams so "opt in to the cloud"
is configuration, not a rewrite.

## Acceptance criteria

- [ ] `docs/DEPLOYMENT.md` (in the mkdocs nav): the component→service mapping
      (narration/embedding models → GenAI Hub on AI Core; graph + future
      vector store → HANA Cloud; platform context → BTP), the local-first
      principle, the full env-var configuration reference, a step-by-step
      provisioning runbook, and an honesty note separating what CI exercises
      (adapters against fakes) from what needs real credentials.
- [ ] `tessera/platform/`: `config.py` (env-derived `PlatformConfig`; the
      provider selection defaults to **none**) and `providers.py` (a
      `ModelProvider` protocol; `GenAIHubProvider` speaking AI Core's
      OAuth2 client-credentials + deployment inference shape; an
      `AnthropicProvider` fallback so narration is demoable today —
      maintainer decision). Pure stdlib HTTP; **zero new dependencies**.
- [ ] Providers are constructed only from explicit config; with no env set,
      `provider_from_env()` returns `None` and nothing touches the network.
      CI stays key-free; tests inject a fake transport and pin request
      shapes (URLs, headers, payloads) and error degradation.
- [ ] ADR 0012 records the design and the non-decisions (no HANA persistence
      seam yet — the graph stays in-process per ADR 0004; the vector path
      arrives with embeddings per ADR 0010's trigger).
- [ ] Eval numbers untouched.

## Scope

**In:** the deployment doc, the platform config/provider seam + tests,
ADR 0012, nav/index updates.

**Out:** provisioning anything (asked and declined); a HANA persistence layer
or storage interface (speculative until embeddings/persistence have a measured
need — building dead code to look deployed is the overclaiming CLAUDE.md
forbids); consuming the provider in the conversational surface (Unit 6, spec
0040); SDK dependencies (`ai-core-sdk`, `anthropic`) — stdlib HTTP keeps
clone-and-run pure and the request shapes visible.

## Eval impact

None. The platform seam is dormant until Unit 6 wires narration, and even
then claims remain deterministic and verifier-checked.

## Risks / open questions

- API shapes drift (AI Core inference paths, Anthropic versions). Mitigated:
  the shapes live in one small module with the version constants named, and
  the doc states which API versions were targeted.
- The GenAI Hub adapter cannot be integration-tested without credentials —
  stated honestly in DEPLOYMENT.md; the fake-transport tests pin our side of
  the contract.
