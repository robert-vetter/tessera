# 0055. HANA-native embedding (VECTOR_EMBEDDING) — the GenAI Hub → HANA pivot

- **Phase / milestone:** Milestone 6 — Embeddings on SAP (Unit 5 of 9; plan 0051)
- **Issue:** —
- **Status:** approved (autonomous mode; maintainer pivot recorded below)

## Problem

ADR 0015 chose *GenAI Hub generation + HANA storage*. In practice the GenAI Hub
embedding deployment proved hard to configure and did not work for the
maintainer; provisioning + a second auth flow + a service key is a lot of moving
parts for what is, at our scale, an easy semantic task. **Maintainer decision
(asked, project-shaping — external service): drop GenAI Hub; generate embeddings
*inside HANA* with its `VECTOR_EMBEDDING()` function.** This is the in-database
alternative ADR 0015 considered and rejected — the pivot and its reason are
recorded in an ADR 0015 addendum.

This is not a weaker "ran on SAP" story; arguably it is cleaner — a **single**
SAP service (HANA Cloud's native vector engine, including its embedding
function) does the whole semantic-retrieval job, on the credentials we already
have working. It still closes the error-class-synonymy miss (ADR 0010), still
keeps faithfulness structural and embedding-free, and unblocks the milestone on
HANA alone (no AI Core key).

This unit adds the HANA-native retrieval path; the eval wiring + the synonymy
gold case + the precision guard are U6; the recorded run is U8.

## Acceptance criteria

- [ ] A `SemanticRetriever` `Protocol` (`retrieve(question, k) ->
      list[(EvidenceRecord, float)]`) so callers are polymorphic over the two
      backends.
- [ ] `HanaSemanticIndex` in `tessera/semantic.py`: in-SQL embedding so vectors
      never round-trip through Python — `index()` does
      `UPSERT … VALUES (?, VECTOR_EMBEDDING(?, 'DOCUMENT', '<model>')) WITH PRIMARY KEY`
      (table created `(ID, VEC REAL_VECTOR)`, guarded by a `SYS.TABLES` check);
      `retrieve()` does `SELECT TOP k ID, COSINE_SIMILARITY(VEC,
      VECTOR_EMBEDDING(?, 'QUERY', '<model>')) … ORDER BY … DESC`. Injected
      `connect` so the SQL contract is tested against a fake — key-free, offline.
- [ ] The model name is config (`HANA_EMBEDDING_MODEL`, default
      `SAP_NEB.20240715`) and **validated** (`^[A-Za-z0-9_.]+$`) before being
      interpolated as a SQL literal — no injection through a controlled value.
- [ ] `TESSERA_EMBEDDINGS` gains `hana`; `build_semantic_index` selects:
      `hana` → `HanaSemanticIndex`; `genai-hub` → the provider+store path
      (unchanged); `none` → `None` (lexical fallback). The GenAI Hub adapter +
      `HanaVectorStore` stay as the documented, contract-tested **alternative**
      (the seam is not HANA-locked).
- [ ] ADR 0015 addendum records the pivot, the reason, and that both backends
      exist with the recorded run using HANA-native.
- [ ] DEPLOYMENT env table gains `HANA_EMBEDDING_MODEL` and the `hana` selector
      value, and notes the **NLP feature** must be enabled on the instance for
      `VECTOR_EMBEDDING()`.

## Scope

**In:** `SemanticRetriever` protocol + `HanaSemanticIndex` + `build_semantic_index`
mode selection + model validation; `HANA_EMBEDDING_MODEL` + `EMBEDDINGS_HANA`
config; promote `hdbcli_connect` to shared; ADR 0015 addendum; DEPLOYMENT rows;
`tests/test_semantic.py` SQL-contract + mode-selection + validation tests.

**Out:** harness wiring + the synonymy gold case + the precision guard (U6); the
live run (U8). No battery numbers move here. The GenAI Hub path is **kept**, not
removed.

## Eval impact

None. The default (no embeddings) stays lexical; every battery 1.000. The HANA
path is inert without `TESSERA_EMBEDDINGS=hana` + HANA creds; its recall gain is
measured online in U8.

## Risks / open questions

- **`VECTOR_EMBEDDING` signature/model are SAP-version-specific.** The documented
  form is `VECTOR_EMBEDDING(text, 'DOCUMENT'|'QUERY', 'SAP_NEB.20240715')`; the
  model name is config + confirmed at the U8 smoke test against the live
  instance. The contract test pins the SQL *shape* we emit.
- **Requires the HANA NLP feature enabled** (the toggle we skipped at
  provisioning). A reversible instance edit; called out in DEPLOYMENT and U8.
- **Model name is interpolated, not bound** (the function's 3rd arg is a
  literal). Mitigated by the `^[A-Za-z0-9_.]+$` validation on a controlled config
  value; the text and query are bound parameters (no injection surface).
- **`REAL_VECTOR` declared without a fixed dimension** so the table accepts the
  model's native dimension; confirmed at the live run.
