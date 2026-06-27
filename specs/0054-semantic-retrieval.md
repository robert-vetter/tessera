# 0054. Semantic retrieval behind the seam — lexical BM25 stays the fallback

- **Phase / milestone:** Milestone 6 — Embeddings on SAP (Unit 4 of 8; plan 0051)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

Units 2–3 built the two seams (text → vector; store + KNN). This unit composes
them into a **retrieval capability** that surfaces evidence by *meaning*, and
makes the fallback explicit: when embeddings are unconfigured (the default,
offline, CI), retrieval is the existing lexical BM25 (ADR 0003); when they are
configured, the engine can retrieve semantically and bridge vocabulary the
lexical path cannot (the error-class-synonymy miss, ADR 0010/0015).

Crucially, this unit keeps embeddings on the **retrieval** side of a hard line:
they change *which records are surfaced*, never *what is claimed or how a claim
is verified*. The faithfulness verifier stays deterministic, structural, and
**embedding-free** — pinned here by a leak-guard test that becomes a standing
invariant for the rest of the milestone.

## Acceptance criteria

- [ ] A vertical-neutral `tessera/semantic.py`: `SemanticIndex` (embed records
      via an `EmbeddingProvider`, store via a `VectorStore`, retrieve by KNN,
      returning `list[tuple[EvidenceRecord, float]]` — the same shape as
      `retrieval.retrieve`).
- [ ] `build_semantic_index(records, *, config, provider, store)` →
      `SemanticIndex | None`: `None` in the default local mode (no embedding
      provider); otherwise embeds + indexes the records. Store defaults to HANA
      when `HANA_HOST` is set, else the in-memory backend. `provider`/`store`
      are injectable for offline testing.
- [ ] `semantic_or_lexical(question, kb, *, k, index)`: returns the semantic
      hits when an index is present, else falls back to `retrieve(question, kb,
      k)`. One obvious place the decision lives.
- [ ] **Leak-guard test (standing invariant):** a subprocess imports only
      `tessera.eval.metrics` and asserts `tessera.semantic`,
      `tessera.platform.vectors`, and `tessera.platform.providers` are **absent**
      from `sys.modules`. A faithfulness 1.0 can never be produced by a model.
- [ ] Mechanism tests with a deterministic **stub embedder** (no network):
      semantically-related phrasings that share *no lexical token* are retrieved
      together where BM25 would miss them; the fallback returns lexical results
      when no index is present.

## Scope

**In:** `tessera/semantic.py` (index + factory + fallback helper);
`tests/test_semantic.py` (mechanism, fallback, leak-guard).

**Out:** wiring semantic retrieval into the github_actions / devex answer paths
and the eval battery (U5 — where the synonymy gold case and the **precision
guard** live); the live GenAI Hub / HANA run (U7). No battery numbers move in
this unit; no engine claim path changes. The stub embedder proves the
*mechanism*, not that the real model closes the synonymy — that is U7's recorded
measurement.

## Eval impact

None. The default (no embeddings) keeps the lexical path and every battery at
1.000; the semantic path is inert without configuration. The recall gain is
demonstrated as a mechanism here and *measured* in U5/U7.

## Risks / open questions

- **The stub embedder must not be mistaken for the result.** It is a
  keyword-axis toy that proves "embed → KNN → record" works and that a model
  which places synonyms near each other would retrieve the right evidence. The
  honest closure of the synonymy is the recorded online run (U7), not this test.
- **Core dependency direction:** `semantic.py` depends on the platform seam
  (vertical-neutral infrastructure) and on `retrieval.retrieve` (core) — no
  vertical logic enters, so the ADR 0008 boundary holds. Embeddings are an
  infrastructure capability, not vertical behaviour.
- **The leak-guard is the milestone's spine.** If a later unit makes the
  verifier import an embedding module, this test fails — by design.
