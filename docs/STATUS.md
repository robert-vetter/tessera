# Status

Living session journal. Append a new dated entry at the end of every work session via `/wrap`. Newest at the bottom. This file is the project's working memory — any session should be resumable from here without relying on recall.

---

## (date) — Project bootstrapped

**Done this session**
- Repository and design docs in place (`README`, `PROJECT_BRIEF`, `CAPABILITIES`, `SAP_ALIGNMENT`, `ROADMAP`, `ENGINEERING`).
- Claude Code workflow configured: `CLAUDE.md`, `.claude/commands/`, `.claude/settings.json`.
- ADR and spec scaffolding created; ADR-0001 recorded.

**Current eval numbers**
- None yet — eval harness arrives in Phase 1.

**Next**
- Phase 0: reproducible dev environment + a "hello world" of the conversational surface answering one hardcoded grounded question end-to-end. See `docs/ROADMAP.md`.

**Open questions / risks**
- Confirm SAP AI Core / HANA Cloud access path for later phases; not blocking local development.

**State of the tree**
- `main` green, no open branches.

---

## 2026-06-05 — Phase 0 complete (tooling skeleton + grounded hello-world)

**Done this session**
- Built the entire Phase 0 scaffolding as nine verified units, each via
  `/spec → /plan → implement → /verify → /commit`, on branches → PRs → CI-green →
  squash-merge once branch protection was enabled:
  1. uv-managed Python project — ruff, mypy (strict), pytest; Python pinned to
     3.12; `uv.lock` committed (`562cad4`, spec 0001).
  2. Pre-commit hooks — ruff, gitleaks, file hygiene (`02d10fb`, spec 0002).
  3. CI workflow — `gate` mirroring the local gate on every PR/push (`498a237`,
     spec 0003).
  4. Dockerfile + devcontainer — reproducible, non-root (`743d5c4`, PR #1, spec 0004).
  5. MkDocs Material site + Pages deploy — **live** at
     https://robert-vetter.github.io/tessera/ (`d247428`, PR #2, spec 0005).
  6. CHANGELOG — Keep a Changelog, seeded (`0d810e0`, PR #3, spec 0006).
  7. Issue/PR templates + Dependabot (github-actions/uv/docker) (`51b646d`,
     PR #4, spec 0007).
  8. README badges — CI, Docs, License (`fd5200e`, PR #7, spec 0008).
  9. Hello-world grounded-answer surface — `uv run tessera`, claim-level
     provenance + principled refusal, deterministic/LLM-free (`17f5574`, PR #8,
     spec 0009).
- Merged two Dependabot PRs bumping pinned actions to Node-24 versions
  (`checkout` v6.0.3 #5, `cache` v5.0.5 #6), clearing the Node-20 deprecation.
- Enabled (manual, by maintainer): branch protection requiring `gate` + PRs;
  GitHub Pages with the GitHub Actions source.

**Current eval numbers**
- None yet — the eval harness arrives in Phase 1. Unit 9 established the
  provenance contract the faithfulness metric will measure ("no claim without
  evidence"), enforced as a type invariant + tests.

**Next**
- **Phase 1 — the thin vertical slice** (Business Data Copilot). First unit of
  work: ingest **one** structured + **one** unstructured source through a single
  intake path into a common internal representation that preserves origin
  metadata (per `docs/ROADMAP.md` Phase 1 and `docs/CAPABILITIES.md` Pillar 1).
  The grounding core in `src/tessera/grounding.py` (EvidenceRecord/Claim/Answer)
  is the shape to grow real ingestion + retrieval into. The eval harness (small
  gold set + a first faithfulness number) is the other Phase 1 milestone.
- Start the next session with `/spec` for the ingestion unit.

**Open questions / risks**
- **Provenance data model** is the one durable design choice from Phase 0; if it
  proves load-bearing once real ingestion/retrieval land, record it with `/adr`
  in Phase 1 (flagged in spec 0009).
- Dependabot **security alerts** are disabled (separate from version updates,
  which work); enable in repo settings if CVE notifications are wanted.
- Confirm SAP AI Core / HANA Cloud access path for later phases; not blocking
  local development.

**State of the tree**
- `main` green and in sync with `origin/main`; no open branches. Tagged `phase-0`.

---

## 2026-06-05 — Phase 1 Units 1 + 1b (structured ingestion + eval scaffold)

**Done this session**
- **Unit 1 — structured ingestion into a common representation** (PR #10,
  squash-merge `9315da3`, spec 0010, ADR 0002):
  - Engine grew a provenance core: `Origin{source, locator, ingested_at}` + a
    **modality-agnostic, kind-tagged `Locator`**; `EvidenceRecord` now *requires*
    an origin, so "no information without a retrievable origin" (Pillar 1) holds
    by construction. The locator is shaped to also hold a document's
    page/line/chunk (Unit 2) with no restructuring — proven in code by
    `test_locator_is_modality_agnostic`. ADR 0002 records this with rejected
    alternatives (bare `source:str`, flat optional fields, stringly-typed locator,
    closed tagged union).
  - `ingestion.py`: the vertical-neutral `Ingester` "one door" + a stdlib CSV
    reader. `sources/salt.py`: a **schema-faithful** ingester (stable natural-key
    ids). `knowledge.py` now *ingests* and wires the demo question to real rows —
    **no hardcoded evidence remains**.
  - **Data decision pivoted A→B.** Real SALT is access-gated on HF (HTTP 401) and
    redistributing a derived sample is legally unclear + breaks clone-and-run, so
    we generate **synthetic data on SALT's real schema** under `data/salt_synthetic/`
    (331 rows, 4 tables, deterministic via `scripts/generate_salt_synthetic.py`,
    stdlib). Names/addresses carry deliberate entity-resolution difficulty
    (GmbH/Gmbh/G.m.b.H, umlaut folds, abbreviations, typos) for Unit 4. Ingesting
    real SALT later is a documented drop-in (gated by HF access only). See
    `data/salt_synthetic/NOTICE`; code MIT, synthetic data carries no encumbrance.
- **Unit 1b — eval-harness scaffold** (PR #11, squash-merge `2289ac1`, spec 0011,
  no ADR): `tessera.eval` (`GoldCase`/`EvalReport`/`load_gold_set`/`run_eval`) +
  `tessera-eval` CLI, **wired as `/verify` step 5** (`.claude/commands/verify.md`
  names the command; "no gold set evaluated yet" is an explicit pass). Honest by
  design — it loads/counts gold cases but does **not** score; metrics stay `None`,
  never fabricated. Gold set location `eval/gold/` (empty). Metric definitions +
  gold set + computation deferred to Unit 6 (ADR-worthy there).

**Current eval numbers**
- Harness runnable; **0 gold cases → faithfulness / coverage / quality: n/a.**
  This is the honest baseline; the first real number arrives in Unit 6.

**Next**
- **Unit 2 — unstructured ingestion.** Author a small set of agreement /
  correspondence documents that reference the **actual** synthetic SALT customers
  (reusing their real name/address variants, so the cross-source link and Unit 4
  entity resolution are genuine), and ingest them through the **same** `Ingester`
  door using the `doc-span` `Locator` kind the representation already supports
  (page/line/chunk). No ADR expected. Start with `/spec`.
- **Then Unit 3** (retrieval; ADR: lexical-first, embeddings deferred) →
  **pause before Unit 4 `/plan`** for the maintainer to review the graph-store +
  entity-resolution data model together → Unit 4 (graph + ER; ADR) → Unit 5
  (cross-source answer composition) → Unit 6 (gold set + faithfulness metric; ADR).

**Open questions / risks**
- **Process gap (flagged, task spawned):** `/verify` verified format/lint via the
  **pre-commit** ruff hook, but CI runs `uv run ruff format --check .` /
  `uv run ruff check .` (uv.lock ruff CLI) — they diverged and CI went red after a
  "green" local verify. Fixed forward this session; a separate task will align
  `/verify` to run CI's exact ruff commands. Until then, run the CI-equivalent
  commands in `/verify`, not only pre-commit.
- The provenance representation (ADR 0002) is now load-bearing; watch that Unit 2
  documents truly fit the `doc-span` locator without reshaping it (the forward-
  compat test guards this).
- Confirm SAP AI Core / HANA Cloud access path for later phases; not blocking.

**State of the tree**
- `main` green and in sync with `origin/main`; no open branches (stale remote-
  tracking refs pruned). Units 1 + 1b merged. Not yet tagged (phase tag is for
  end of Phase 1).

---

## 2026-06-05 — Phase 1 Units 2 + 3 (unstructured ingestion + lexical retrieval)

**Done this session**
- **Unit 2 — unstructured ingestion** (PR #13, squash-merge `f2e26b0`, spec 0012,
  no ADR): documents arrive through the **same `Ingester` door** as structured
  data. `ingestion.chunk_text()` (generic paragraph chunker), `Locator.doc_span()`
  (line range + chunk — the unstructured counterpart to `table_row()`, **no**
  `EvidenceRecord`/`Origin` change, cashing in ADR 0002's forward-compat), and
  `sources/documents.py` `DocumentSource`. Corpus `data/business_docs/` (3 authored
  agreements/correspondence) references the real synthetic customers under
  **variant** forms — one ("Lumière Énergie") resolvable only by real ER — and
  carries info the tables **lack** (renewal/terms/discounts). Both properties
  tested.
- **Unit 3 — lexical retrieval** (PR #14, squash-merge `bd4cb08`, spec 0013, ADR
  0003): replaced the Phase-0 hand-authored question→claim map with a real
  retriever. New `retrieval.py` — Okapi **BM25**, pure-stdlib, **deterministic, no
  model/network**; `retrieve()` + `answer()` surface retrieved records as sourced
  claims and **refuse** on zero content-token overlap (principled, threshold-free).
  Removed `Fact`; `KnowledgeBase` is records-only; `answer()` moved out of
  `grounding`. ADR 0003 records lexical-first with a measured **revisit trigger**
  and rejected alternatives.

**Current eval numbers**
- Harness runnable; **0 gold cases → faithfulness / coverage / quality: n/a.**
  Unchanged this session by design (gold set + metrics are Unit 6). Unit 3 is the
  first behaviour the **coverage**/refusal metric will measure once it exists.

**Honest behaviour note (not a regression)**
- The answer now **surfaces retrieved, sourced evidence**; it does **not**
  synthesise prose or compute aggregates (the precomputed "combined value EUR
  45,000" is gone — that's multi-step reasoning, Phase 2). Term-frequency ranking
  means leading a query with a customer name surfaces customer *rows* above the
  substantive clause; tying entity *variants* to one identity is **Unit 4's** job.

**Next**
- **Unit 4 — knowledge graph + basic cross-source entity resolution.** Build a
  minimal graph linking the same real-world entity across the two sources
  (customer master ↔ address master ↔ document references under variant forms),
  **recording each merge decision and its confidence so they stay inspectable and
  reversible** (CAPABILITIES Pillar 2). SALT-KG metadata graph is a candidate
  reference. Carries an **ADR** (graph-store choice + ER data model).
  **PROCESS GATE:** before Unit 4's `/plan`, pause for a maintainer review of the
  graph-store choice and the ER/merge-confidence data model *together* — no code
  until that's settled. Flow: `/spec` → design review → `/plan` → implement.
- Then **Unit 5** (single claim combining a row + a clause across sources) and
  **Unit 6** (curated gold set + the faithfulness/coverage/quality metrics; ADR).

**Open questions / risks**
- **ER is the hard part.** Variant forms are deliberately nasty (typos, umlaut
  folds, dropped legal forms, plus duplicate customers e.g. four "Bayerische
  Stahlwerke" rows). Be honest about precision/recall; record merges as fallible.
- **Retrieval revisit trigger (ADR 0003):** if Unit 6's coverage shows lexical
  retrieval missing present evidence (vocabulary/variant mismatch not absorbed by
  Unit 4), reconsider semantic/embedding retrieval.
- **Process gap (still open, task spawned):** `/verify` uses the pre-commit ruff
  hook; CI uses `uv run ruff format --check .` / `ruff check .`. Continue running
  the CI-equivalent commands in `/verify` until the gate is aligned.
- Confirm SAP AI Core / HANA Cloud access path for later phases; not blocking.

**State of the tree**
- `main` green and in sync with `origin/main`; no open branches. Units 1, 1b, 2, 3
  merged (PRs #10–#14). Five of six Phase 1 units done. Not yet tagged.

---

## 2026-06-09 — Phase 1 Unit 4 (knowledge graph + non-destructive entity resolution)

**Done this session**
- **Unit 4 — knowledge graph + basic cross-source entity resolution** (PR #16,
  squash-merge `c74dad7`, spec 0014, ADR 0004). Reviewed the graph-store choice
  and ER/merge model with the maintainer before any code (the standing gate), with
  four fixed design constraints:
  - **Embedded / in-process graph** (`src/tessera/graph.py`) — `KnowledgeGraph`
    with `Node`/`Edge`/`Resolution`/`Mention`. No Neo4j/HANA; HANA persistence is
    ADR future work. SALT foreign keys become deterministic structural edges
    (`sources/salt.py` now exposes `org_names()` + `structural_edges()`, keeping
    schema knowledge in the source, engine vertical-neutral).
  - **Non-destructive resolution layer** — a `Resolution` is an *additive*
    assertion that two org-name nodes co-refer, carrying a reason (matched
    normalized forms + score) and a confidence. Resolved entities are connected
    components, **derived not stored**; `remove_resolution()` re-splits a cluster
    and leaves raw records intact. Nothing is collapsed/overwritten. Document
    references link via additive `Mention`s.
  - **Deterministic, explainable, name-only matching** (`src/tessera/resolution.py`)
    — umlaut/case fold + `difflib` similarity, with a named/tunable
    `DEFAULT_RESOLUTION_THRESHOLD = 0.85`. No embeddings/ML. Confidence is the
    similarity score used as a **proxy, not a calibrated probability**.
  - **Scope ended at graph + resolution** — answer composition is Unit 5.
  - Proof tests (all green): Bayerische/Bayersche/Bayerische (customers +
    addresses) → one entity w/ reasons+confidence; Müller customer + Mueller
    address → one entity; Müller vs Nordwind ("… Logistik GmbH") stay separate;
    assertion withdrawal re-splits with raw data intact; MSA chunk links
    cross-source to the Müller entity; Lumière letter is a documented, tested known
    recall miss.

**Current eval numbers**
- Harness runnable; **0 gold cases → faithfulness / coverage / quality: n/a.**
  Unchanged by design (metrics are Unit 6). Unit 4 builds the entity layer the
  Unit 6 metrics (and a possible ER precision/recall check) will measure.

**Phase 1 engine status**
- End-to-end now exists: ingest both modalities → one graph with resolved entities
  → deterministic lexical retrieval with provenance → principled refusal → runnable
  eval. Five of six units done (1, 1b, 2, 3, 4).

**Next**
- **Unit 5 — cross-source answer composition.** Compose a single grounded answer
  that combines a database **row** and a document **clause** about the *same
  resolved entity* — e.g. Müller Logistik's sales orders (SALT rows) *and* its
  master service agreement's renewal terms (MSA clause) — each claim still carrying
  claim-level provenance, traversing the graph's resolved-entity clusters +
  `Mention` links built in Unit 4. This brings back the synthesis Unit 3 honestly
  deferred. Likely no ADR (builds on 0002/0003/0004); confirm at `/spec`.
- **Then Unit 6** — curated gold set + the faithfulness/coverage/quality metrics
  (ADR-worthy), turning `tessera-eval`'s "n/a" into a real number and closing
  Phase 1.

**Open questions / risks**
- **ER precision/recall is honest, not maximal** (ADR 0004): single name-similarity
  threshold; transitive-closure over-merge possible; name-only (multi-field is
  additive future work); document-mention recall misses forms absent from master
  data (the Lumière case). Unit 6's metric is the revisit trigger for the threshold
  and for embeddings/ML.
- **Retrieval revisit trigger (ADR 0003)** still stands for Unit 6 coverage.
- **Process gap (open, task spawned):** `/verify` uses the pre-commit ruff hook; CI
  runs `uv run ruff format --check .` / `ruff check .`. Keep running the
  CI-equivalent commands in `/verify` until the gate is aligned.
- Confirm SAP AI Core / HANA Cloud access path for later phases; not blocking.

**State of the tree**
- `main` green and in sync with `origin/main`; no open branches. Units 1, 1b, 2, 3,
  4 merged (PRs #10–#16). Five of six Phase 1 units done. Not yet tagged (tag at
  end of Phase 1).
