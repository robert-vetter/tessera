# Architecture Decision Records

An ADR captures a single decision that is **expensive to reverse**, the context that forced it, and the alternatives that lost. We keep them so that the answer to "why is it built this way?" is always written down rather than reconstructed from memory.

## Rules
- One decision per record. Numbered sequentially: `0001-…`, `0002-…`.
- **Append-only.** A decision that no longer holds is marked `superseded by NNNN` — never edited away or deleted. The trail of changed minds is part of the value.
- Short and concrete. A record, not an essay.
- Create new ones with the `/adr` command, using `0000-template.md`.

## When to write one
- Choosing a storage or graph technology.
- Choosing how grounding / provenance works.
- Defining or changing an eval metric.
- Any structural choice that later code will depend on.

## Index
- [0001](0001-record-architecture-decisions.md) — Record architecture decisions
- [0002](0002-ingestion-provenance-representation.md) — Ingestion & provenance representation
- [0003](0003-lexical-first-retrieval.md) — Lexical-first retrieval; semantic deferred
- [0004](0004-graph-and-entity-resolution.md) — In-process graph + non-destructive entity resolution
- [0005](0005-faithfulness-metric.md) — The faithfulness metric
- [0006](0006-deterministic-reasoning-llm-deferral.md) — Deterministic question understanding; LLM deferred
- [0007](0007-synthetic-scenario-generation.md) — Synthetic eval scenarios, enumerated from the graph
- [0008](0008-vertical-boundary.md) — The core/vertical boundary (Phase 3)
- [0009](0009-multi-vertical-eval-batteries.md) — Eval batteries: how verticals are measured
- [0010](0010-declared-aliases-before-embeddings.md) — Declared aliases before embeddings (Phase 4)
- [0011](0011-vertical-owned-claim-grammars.md) — Vertical-owned claim grammars
- [0012](0012-sap-deployment-path.md) — SAP deployment path: docs + tested seams
- [0013](0013-narration-boundary.md) — The narration boundary: rephrase, never add
- [0014](0014-real-connector-snapshot-boundary.md) — Real connector: fetch-to-snapshot, ingest raw (Milestone 5)
- [0015](0015-embeddings-on-sap.md) — Embeddings on SAP: GenAI Hub + HANA vector, lexical fallback (Milestone 6)
- [0016](0016-embedding-assisted-entity-resolution.md) — Embedding-assisted entity resolution: stem-gated, additive (Milestone 7)
- [0017](0017-stable-log-chunk-ids.md) — Finer log chunking with stable, role-tagged chunk ids (Milestone 7)
- [0018](0018-stem-gated-deterministic-er.md) — Stem-gated deterministic ER: cure the generic-suffix over-merge (Milestone 8)
- [0019](0019-multi-field-entity-resolution.md) — Multi-field entity resolution: a two-way address gate (Milestone 9)
- [0020](0020-registration-key-entity-resolution.md) — Registration-key entity resolution: the exact decisive field (Milestone 10)
- [0021](0021-heading-leads-its-section.md) — A Markdown heading leads its section, not a chunk of its own (Milestone 11)
- [0022](0022-agentic-mcp-boundary.md) — The agentic boundary: read-only, verifier-checked grounded tools over MCP (Milestone 11)
- [0023](0023-grounded-action-boundary.md) — The grounded-action boundary: propose-and-approve, field-verified actions (Milestone 12)
- [0024](0024-executable-payload-preview.md) — The executable-payload boundary: a dry-run preview, render ≠ send (Milestone 13)
- [0025](0025-execution-behind-approval.md) — The execution boundary: effectful execution behind approval, simulated by default (Milestone 14)
- [0026](0026-best-effort-idempotency.md) — Best-effort client-side idempotency on the real execution path (Milestone 15)
- [0027](0027-stdlib-web-ui.md) — The web surface: pure stdlib, zero JavaScript, no credential (Milestone 17)
- [0028](0028-byo-connector-workspace-boundary.md) — BYO connect: fetch-to-local-workspace, offline answers, optional no-scope token (Milestone 18)
- [0029](0029-declared-ingest-config.md) — `tessera ingest <dir>` driven by a declared stdlib-TOML config (Milestone 18)
- [0030](0030-hana-kg-persistence-boundary.md) — Knowledge-graph persistence: a mirror on HANA's KG engine, never a source of truth (SAP track S2)
