# 0028. DevEx graph assembly + component entity resolution

- **Phase / milestone:** Phase 3 — second vertical (DevEx Copilot), Unit 3
- **Issue:** —
- **Status:** approved (autonomous mode; decisions recorded here)

## Problem

The ingested DevEx records must become one queryable graph — the *same*
`KnowledgeGraph` machinery, the same non-destructive resolution layer (ADR
0004), no DevEx logic in the engine. The cross-source entity here is the
**service/component**: it appears canonically in the service catalog, in
variant forms in the on-call export, and by name inside log text. Pipelines,
runs, tickets, PRs, log chunks and diff hunks hang off it via deterministic
structural edges, exactly as SALT's foreign keys did.

## Acceptance criteria

- [ ] `tessera/sources/devex.py` (the *source*, where schema knowledge
      lives) gains `org_names()` (catalog names + on-call service names),
      `node_attributes()` (runs: status/failed_job/commit/started; tickets:
      type/status; prs: merged commit), and `structural_edges()`:
      run→pipeline `executes`, pipeline→component `builds`,
      ticket→component `concerns`, PR→ticket `motivated_by` (first
      `DEVEX-\d+` in the description; PR-205 gets none), log-chunk→run
      `log_of`, diff-hunk→PR `diff_of`.
- [ ] `tessera/devex/knowledge.py`: `build_devex_graph()` /
      `build_devex_kb()` mirroring the business assembly — nodes (chunks as
      kind `document` per ADR 0008's convention), edges, then the engine's
      unchanged `resolve_entities()` + `link_document_mentions()`.
- [ ] **Measured ER outcomes pinned by tests:** catalog↔on-call variants
      merge for payments/auth/search/inventory; `checkout-svc` (0.846) and
      `notif-svc` (0.429) stay unresolved — *named misses*; distinct
      services never merge; withdrawal of an assertion re-splits the cluster
      (reversibility intact on DevEx data).
- [ ] Log chunks naming a service link to it via the engine's mention pass.
- [ ] **Zero core changes.**

## Scope

**In:** source accessors, the devex package + assembly, graph/ER tests.
**Out:** answer paths (Units 4–5); routing/CLI (Unit 6); any alias-based
mention enrichment (recorded as future work — the catalog's abbreviation
forms are the misses the metric should *see* first, per ADR 0003/0004
discipline: measure, then improve).

## Eval impact

None yet (nothing consumes the graph until Unit 4). The pinned near-miss at
0.846 is deliberately left unfixed so the DevEx battery can measure it; it
becomes the recorded coverage gap of Unit 8.

## Risks / open questions

- Transitive over-merge risk (ADR 0004) re-checked on DevEx names: max
  cross-service similarity measured 0.78 (`auth-service`/`search-service`)
  — comfortably under 0.85; pinned by test.
- `motivated_by` extraction treats the first `DEVEX-\d+` as the motivating
  ticket ("Fixes"/"Refs" alike) — a deliberate, simple rule recorded here.
