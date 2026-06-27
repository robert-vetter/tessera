# 0015. Embeddings on SAP: GenAI Hub generation + HANA vector, lexical fallback

- **Status:** accepted
- **Date:** 2026-06-27

## Context

ADR 0003 (lexical-first retrieval) and ADR 0010 (declared aliases before
embeddings) both deferred semantic embeddings behind a **measured** trigger:
embeddings arrive only when a coverage miss exists that *no declarable data can
fix*. Milestone 5 produced exactly that, committed as a fact
(`test_adr0010_error_class_synonymy_is_undeclarable`): in the repo's own real
Pages-deploy failure one root cause surfaces as three mutually un-bridgeable
strings — `HttpError: Not Found`, `status: 404`, `Ensure GitHub Pages has been
enabled` (pairwise string-similarity `< 0.35`, all present in the committed
log). A declared catalog alias closes a *name* variance; it cannot declare "404
means Pages-not-enabled." The trigger has fired on an undeclarable miss.

The maintainer authorized crossing the line for this earned case (the two
project-shaping questions of Milestone 6, asked 2026-06-27): act on it the way
ADR 0003/0010 always specified — **SAP Generative AI Hub embeddings + HANA Cloud
vector store, with the lexical path as the portable offline fallback** — and
make it *real* (a recorded online measurement, not a runbook). This is the
**first** time the project takes on a model/cloud runtime dependency; the whole
value of the decision is in where the boundary sits.

## Decision

**Embeddings serve retrieval/linking only — never the claim path.** A semantic
vector decides *what evidence is surfaced or linked*; it never generates,
alters, or judges a claim. The faithfulness verifier (`eval/metrics.py`,
`is_supported`) stays deterministic, structural, and **embedding-free**, pinned
by a leak-guard test (no import from the embedding/vector modules reaches it).
A 1.0 stays earned by structure, not by a model. ADR 0005's LLM-judge stays
deferred — this decision does not touch it.

**Generation at GenAI Hub; storage/search in HANA; lexical as the fallback.**
- Text → vector is a narrow seam (`EmbeddingProvider`, spec 0052), with a
  `GenAIHubEmbeddingProvider` adapter speaking stdlib HTTPS — the exact analogue
  of the `ModelProvider` chat seam (ADR 0012). In-database HANA `VECTOR_EMBEDDING`
  was available but **not** chosen (see alternatives).
- Vectors are stored and KNN-searched in HANA Cloud's core vector engine
  (`REAL_VECTOR` + `COSINE_SIMILARITY`); no NLP/PAL feature, no data lake (spec
  0051). The seam is `VectorStore` (spec 0053).
- When either the embedding provider or the vector store is unconfigured, the
  engine falls back to **lexical BM25** (ADR 0003). The default clone-and-run is
  unchanged: no keys, no model, pure stdlib.

**The cloud dependency is opt-in and contained.** SAP's `hdbcli` HANA driver is
an **optional** extra (`uv sync --extra cloud`), imported lazily inside the HANA
backend, never in the default install or CI import graph (guarded by a test).
`dependencies = []` stays true for the clone-and-run path.

**The number is a recorded online measurement, not a CI-reproducible one.** The
embedding model lives in the cloud and may change; so the close of the synonymy
miss is a **timestamped** point in `eval/history.jsonl` (the Milestone-5
live-fetch precedent), produced by one maintainer-confirmed run. CI stays
key-free on the lexical path, where coverage may honestly read `< 1.0` on the
synonymy case. Faithfulness is gated at 1.0 on every path.

**The close must be earned, not a re-saturation.** A linker strong enough to
bridge `404 ≈ Not Found` could over-merge distinct things. The milestone
measures **precision as well as recall** (spec 0055): the retained `checkout-svc`
0.846 near-miss and distinct services must stay unlinked. A method that fixes one
miss by creating a worse one is a recorded finding that fires a fresh trigger,
not a silently-tuned number.

## Consequences

- **Easier:** the undeclarable miss ADR 0010 named becomes closeable, with a
  real recorded number — "designed for SAP" becomes "ran on SAP." The trust loop
  (measure → name → fix → re-measure) closes on a class of miss declared data
  never could.
- **Easier:** the offline default is untouched — lexical fallback keeps
  clone-and-run, offline CI, and the auditable eval exactly as they were.
- **Accepted cost:** the project now has a cloud/model code path and an optional
  binary dependency. Contained by: retrieval-only scope, opt-in extra, lazy
  import, an explicit selector (`TESSERA_EMBEDDINGS`), and the leak-guard.
- **Accepted cost:** the embedding number is not CI-reproducible. Stated
  honestly wherever it appears; the floor that gates the build stays the
  deterministic lexical path.
- **Accepted cost:** the exact GenAI Hub inference suffix is unverified against
  live SAP until U7; mitigated by `TESSERA_GENAI_EMBEDDING_PATH` + a smoke test
  before the recorded run.
- ADR 0010's refreshed trigger is now **acted on**; ADR 0010 gets an addendum
  pointing here. ADR 0003's "semantic deferred" is partially superseded *for
  retrieval linking on the cloud path only*; the lexical default it chose
  remains the offline path.

## Alternatives considered

- **In-database embeddings (HANA `VECTOR_EMBEDDING`, the NLP feature).** Rejected:
  ties generation to HANA, costs extra memory/licensing, and deviates from the
  ADR 0003/0010 stated end state (GenAI Hub generation). GenAI Hub keeps the
  embedding seam swappable and the HANA role limited to storage/search. (Noted at
  provisioning, spec 0051.)
- **A bundled local embedding model (the no-spend variant).** Rejected for this
  milestone: it would close the miss offline and in CI, but adds a real
  model/runtime dependency to the default path — breaking the pure-stdlib
  clone-and-run identity — and is still only "designed for SAP." CLAUDE.md
  sanctions it as a ceiling; the maintainer chose the cloud "ran on SAP" variant
  (spec 0051). Kept on record as the offline-reproducible option if cloud access
  ever lapses.
- **Embeddings on the claim/faithfulness path (LLM-or-vector judged support).**
  Rejected: that is ADR 0005's question, with its own trigger; conflating it with
  retrieval would put a model between a claim and its verdict — the one thing the
  project refuses. Faithfulness stays structural.
- **Lowering the ER threshold instead of embeddings.** Already rejected in
  ADR 0010 and still: no threshold bridges a 0.429/`< 0.35` string gap without
  catastrophic over-merge. The miss is semantic, not a tuning problem.
- **Persisting the whole knowledge graph in HANA now.** Out of scope: only the
  vector store lands. The graph rebuilds deterministically from data each run
  (ADR 0004), so persistence is an optimization, not a need, at this scale.

## Addendum (2026-06-27) — GenAI Hub → HANA-native embeddings

The GenAI Hub embedding deployment proved hard to configure and did not work for
the maintainer; a second auth flow + service key was disproportionate to an easy
semantic task. **Maintainer decision (asked): generate embeddings *in-database*
with HANA's `VECTOR_EMBEDDING()`** — the in-DB alternative *rejected* above. The
reason it lost (a second SAP service, GenAI Hub orchestration) is outweighed in
practice by working on **one** service with credentials already in hand. This is
still "ran on SAP" — arguably more so: a single SAP service does embedding +
storage + KNN.

- **Changes:** the recorded run (spec 0055/0057/0058) uses `HanaSemanticIndex`
  (`VECTOR_EMBEDDING` in SQL), which requires the HANA **NLP feature** enabled.
- **Holds:** embeddings stay retrieval-only and faithfulness stays structural and
  embedding-free (the leak-guard is unchanged); lexical remains the offline/CI
  fallback.
- **Kept, not removed:** the GenAI Hub `EmbeddingProvider` + the external-vector
  `HanaVectorStore` remain the documented, contract-tested **alternative** — the
  seam is not HANA-locked, and the path works if a GenAI-Hub deployment is ever
  wanted.
