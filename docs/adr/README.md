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
