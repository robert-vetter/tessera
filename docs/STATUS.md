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

---

## 2026-06-09 — Phase 1 Unit 5 (cross-source answer composition — the milestone)

**Done this session**
- **Unit 5 — cross-source answer composition** (PR #18, squash-merge `a041154`,
  spec 0015, no ADR). This is the **Phase 1 milestone**: a person asks one
  realistic cross-source question and gets a sourced answer.
  - `src/tessera/composition.py` (vertical-neutral): `resolve_entity()` (longest
    normalized-name overlap, best-match, **refuse on a tie** between distinct
    entities) + `compose()` (identity row-claim + sourced aggregate + document
    clauses). A **separate** `tessera-compose` entry point — no routing from the
    main CLI (routing is Phase 2).
  - `graph.py`: generic `Node.attributes` + `attr()`, and `sources_of()` /
    `mentions_of()` traversal helpers, so composition stays schema-neutral.
  - `sources/salt.py`: `node_attributes()` exposes each sales doc's `net_amount`
    + `currency`. `knowledge.build_demo_graph()` attaches them.
  - data/generator: appended a deterministic **mixed-currency** entity (Atlas
    Trading, one EUR + one USD order); existing rows byte-identical.
  - **Bounded, honest synthesis:** the entity's total net order value is summed
    over its sales rows with **every summand cited — and exactly those rows**;
    across currencies it does **not** invent a total but reports per-currency
    subtotals and states "Refused to sum across EUR and USD". General multi-step /
    multi-entity reasoning and routing remain Phase 2.
  - Two key tests pinned: aggregate == sum of exactly the cited rows (Müller: 5
    orders → EUR 77,500.00); mixed-currency refuses to sum and says why. Plus
    cross-source (row + renewal clause), ambiguous-question refusal, no-entity
    refusal.
  - **Process note:** Unit 5 was first committed on `main` by mistake (forgot to
    branch); branch protection rejected the push — commit moved to a feature
    branch, local `main` reset. Guardrail worked; branch *first* next time.

**Current eval numbers**
- Harness runnable; **0 gold cases → faithfulness / coverage / quality: n/a.**
  Unchanged by design (Unit 6). Unit 5 produced the multi-source answer shape the
  faithfulness metric will score.

**Phase 1 engine status**
- **Complete end-to-end and demonstrable on the milestone question**: ingest both
  modalities → one graph with resolved entities → retrieval / refusal → cross-source
  composed answer with provenance and a fully-sourced aggregate. Units 1, 1b, 2, 3,
  4, 5 done.

**Next**
- **Interstitial small unit — close the `/verify`-vs-CI ruff gap.** Make `/verify`
  run the exact CI commands (`uv run ruff format --check .` / `uv run ruff check .`),
  and confirm the `ruff` pin in `.pre-commit-config.yaml` matches `uv.lock`. Done
  **before** Unit 6 so the gate is identical and trustworthy before the first real
  eval number lands. (Spec → fix → verify → PR.)
- **Then Unit 6 — close Phase 1:** curated gold set + the faithfulness / coverage /
  quality metrics, turning `tessera-eval`'s "n/a" into a real number over the
  composed answers. **Carries an ADR** (the faithfulness-metric definition — the
  project's central auditable contract). Tag `phase-1` at the end.

**Open questions / risks**
- ER precision/recall remains honest-not-maximal (ADR 0004); composition inherits
  it (e.g. an entity whose document reference was a Unit-4 miss has no clause to
  show).
- Retrieval revisit trigger (ADR 0003) still stands for Unit 6 coverage.
- The `/verify`-vs-CI ruff gap is being closed next (above), retiring that
  long-standing open item.
- Confirm SAP AI Core / HANA Cloud access path for later phases; not blocking.

**State of the tree**
- `main` green and in sync with `origin/main`; no open branches. Units 1, 1b, 2, 3,
  4, 5 merged (PRs #10–#18). Phase 1 milestone met; Unit 6 (eval metrics) remains.
  Not yet tagged.

---

## 2026-06-09 — Phase 1 COMPLETE (Unit 6: eval metrics + gold set; first real numbers)

**Done this session**
- Closed the **`/verify`-vs-CI gate gap** (PR #20, `f34f367`, spec 0016): a shared
  `scripts/gate.sh` is the single source of truth both `/verify` and CI run, so
  local green == CI green. (Done before the first eval number, deliberately.)
- **Unit 6 — evaluation harness v1** (PR #21, squash-merge `a3064b1`, spec 0017,
  ADR 0005): the first real, auditable trust numbers.
  - `eval/metrics.py` `is_supported()` — a deterministic, four-shape faithfulness
    verifier (snippet/clause containment, aggregate recomputation, count match,
    refuse-to-sum condition), written **first** with its adversarial test: an
    injected unfaithful claim is caught, so a 1.0 is **earned, not tautological**.
  - `eval/harness.py` scores faithfulness/coverage/quality over six curated gold
    cases (both answer paths + all three refusal kinds); `eval/cli.py` reports them
    and **exits non-zero if faithfulness < 1.0** (the one hard floor).
  - Fixed the composition **identity claim** to cite the address records it asserts
    — the under-citation the verifier caught. The eval did its job.

**Current eval numbers (first real baseline)**
- **Faithfulness 1.000** (gated; provably able to fail).
- **Coverage 0.929** (honest — the documented Lumière document-mention miss; a real
  number to improve).
- **Quality 1.000** (gold answers correct / refusals refused).

**Phase 1 — DONE.** The whole engine runs end-to-end and is measured: ingest both
modalities through one door → one knowledge graph with non-destructive,
reversible cross-source entity resolution → deterministic lexical retrieval with
principled refusal → cross-source composed answers with claim-level provenance and
a fully-sourced aggregate → faithfulness/coverage/quality with a gated faithfulness
floor. Tagged `phase-1`.

**Next — Phase 2 (deepen trust and reasoning).** Per ROADMAP: question routing
(simple vs. multi-step), multi-step reasoning across several entities and both
modalities, principled refusal under insufficient evidence, **synthetic data
generation** feeding the harness (including ambiguous entities, missing evidence,
conflicting sources), and the trust metrics automated and tracked over time. The
ADR-recorded revisit triggers come due here: embeddings/semantic retrieval (ADR
0003), embeddings/ML + multi-field entity resolution (ADR 0004), and LLM-judged
faithfulness (ADR 0005) — each to be reconsidered when the metric shows the
deterministic approach missing. Start Phase 2 with a roadmap re-read + `/spec`.

**Open questions / risks**
- The Phase-1 metrics are an honest *baseline*, not a ceiling: faithfulness is a
  structural (not semantic) check; coverage 0.929 reflects real, named gaps. Phase
  2 should grow coverage/quality and, when justified, upgrade the methods per the
  revisit triggers.
- Confirm SAP AI Core / HANA Cloud access path for Phase 4 deployment; not blocking.

**State of the tree**
- `main` green and in sync with `origin/main`; no open branches. Units 1, 1b, 2, 3,
  4, 5, 6 + the gate unit merged (PRs #10–#21). **Phase 1 complete; tagged
  `phase-1`.**

---

## 2026-06-10 — Phase 2 COMPLETE (autonomous run: trust deepened and measured over time)

**Mode note:** this phase ran **autonomously** per the new CLAUDE.md
"Autonomous phase execution" section (spec 0018): one kickoff, all units through
spec → implement → gate → PR → CI → merge, decisions recorded in specs/ADRs
instead of asked.

**Done this session (7 units, PRs #23–#29)**
- **Process + drift** (spec 0018, `a6cf512`): autonomous mode codified; ADRs
  0002–0005 added to the docs nav; CHANGELOG rolled into phase-tag sections
  with the missing Phase 1 entries.
- **Multi-step reasoning** (spec 0019, ADR 0006, `a75fba9`): compare two named
  entities + currency-scoped superlative, fully sourced, refusing on
  incomparability; faithfulness verifier recomputes both conclusion shapes
  over the graph, adversarially tested. Also fixed a real hash-seed flake
  (display-name tie-break depended on frozenset iteration order).
- **Question routing** (spec 0020, `23c8a1c`): `uv run tessera` is one routed
  door (multi / entity / lookup), printing route + reason; `--engine`
  overrides; harness accepts `engine: route`.
- **Conflicting evidence** (spec 0021, `c9a03a8`): deliberate renewal-date
  conflict in the corpus (MSA 1 August vs Amendment 1 February); composition
  surfaces a conflict claim citing both sides and refuses a single date;
  verifier covers the shape; gold case 07.
- **Synthetic battery** (spec 0022, ADR 0007, `1fe51a0`): ~52 cases enumerated
  deterministically from the graph at eval time; expectations data-derived
  (anti-tautology); gold and synthetic scored separately; floor gates both.
- **Metrics over time** (spec 0023, `c7950b6`): append-only
  `eval/history.jsonl` + `tessera-eval --record --note`; the README
  faithfulness badge ships (earned since Phase 1; green only while the floor
  holds).
- **Coverage gap closed** (spec 0024, ADR 0004 addendum, `8035a2f`): NFKD
  diacritic folding + suffix-tolerant document mentions (confidence 0.9,
  reason annotated) link the Lumière letter.

**Current eval numbers (recorded in eval/history.jsonl)**
- **Gold (7 cases): faithfulness 1.000 (gated) · coverage 1.000 · quality 1.000.**
- **Synthetic (52 cases): faithfulness 1.000 (gated) · coverage 1.000 · quality 1.000.**
- Trend: coverage **0.929 → 0.938 → 1.000** — the milestone's "visibly
  improved since Phase 1", literally visible in the journal.

**Phase 2 milestone check (ROADMAP)**
- Routing distinguishes lookups from multi-step ✓; multi-entity reasoning ✓
  (compare/superlative over structured rows; the document side participates
  via composition and conflict surfacing — deeper *mixed-modality multi-hop in
  one question* is an honest gap, natural Phase 3+ work); principled refusal
  across five kinds ✓; synthetic generation incl. tricky cases ✓; metrics
  defined, automated, tracked ✓. **Milestone met.** Tagged `phase-2`.

**Open questions / risks**
- Synthetic battery is green across the board — ADR 0007's saturation trigger
  is one phase away; Phase 3's new vertical (DevEx) will stress it naturally.
- ADR 0006/0003 LLM/embedding triggers: still not fired (deterministic layer
  has no measured miss). Revisit when DevEx log/diff phrasing arrives.
- Confirm SAP AI Core / HANA Cloud access for Phase 4; not blocking.

**Next — Phase 3 (second vertical: DevEx Copilot).** Per ROADMAP: ingest CI/CD
logs, PR diffs, and ticket history **through the same doors**; root-cause
hypotheses for failed pipelines grounded in logs and linked to prior
incidents; PR change-summaries tying diffs to tickets; the eval harness
extended to the new vertical. The engine must stay general (principle 5) —
phase success is *two genuinely different verticals on one unchanged core,
both measured*.

**State of the tree**
- `main` green and in sync; no open branches. PRs #23–#29 merged. Tagged
  `phase-2`.

---

## 2026-06-10 — Phase 3 COMPLETE (autonomous run: the DevEx vertical on a provably unchanged core)

**Mode note:** ran **autonomously** end-to-end from one kickoff (per
CLAUDE.md "Autonomous phase execution"): ten units, each spec → branch →
implement → gate → PR → CI-green → squash-merge; decisions recorded in
specs/ADRs instead of asked.

**Done this session (10 units, PRs #31–#40)**
- **Phase plan + the boundary** (spec 0025, ADR 0008, ADR 0009, PR #31):
  what "core" means, what "unchanged" will be proven by, and the only two
  sanctioned vertical-neutral core deltas — fixed *before* any DevEx code.
  Also repaired ADR-index/mkdocs-nav drift.
- **DevEx synthetic corpus** (spec 0026, PR #32): runs+logs, PRs+diffs,
  tickets, service catalog, on-call export — generated with **no RNG**,
  every record a reviewable literal; recurrence anchors (R-0987/R-1042 +
  incident DEVEX-187; search R-1023/R-1031), PR↔ticket refs (PR-205
  deliberately none), ER variants with *measured* outcomes
  (checkout-svc 0.846 near-miss; notif-svc 0.429 miss).
- **Ingestion through the same door** (spec 0027, PR #33): eight source
  shapes as `EvidenceRecord`s; new `log-span` / `diff-hunk` locator kinds on
  the unchanged kind-tagged `Locator` (ADR 0002 cashed a third time).
- **One graph, measured ER** (spec 0028, PR #34): engine's unchanged
  resolve/mention layers over catalog+on-call names; variants merge
  (1.000/0.960), abbreviations stay unresolved as named misses; worst
  cross-service similarity < 0.80; reversibility re-proven on DevEx data.
- **RCA + the shared-fragment shape** (spec 0029, PR #35): the ONE verifier
  delta — generic `"FRAGMENT" appears in 'A' and 'B'` recomputation,
  adversarially tested vertical-free; `tessera/devex/rca.py` answers "why
  did run X fail / has it happened before" with run row, error log lines,
  recurrence + documented-incident claims; first occurrences get no
  recurrence claim; passed runs are refused premises.
- **Change summaries** (spec 0030, PR #36): PR row + diff hunk-by-hunk +
  verified motivating-ticket link; honest omission for PR-205.
- **The second routed door** (spec 0031, PR #37): `uv run tessera-devex`
  (rca / summary / lookup-with-refusal), reasons printed; core routing.py
  untouched.
- **Eval batteries** (spec 0032, ADR 0009, PR #38): harness parameterized
  over per-vertical batteries; gold moved to `eval/gold/business/`; history
  schema v2 (append-only, v1 intact); badge = min gold faithfulness.
  Business numbers reproduced exactly through the refactor (pinned).
- **The DevEx battery** (spec 0033, PR #39): 7 gold cases (incl. the named
  coverage miss) + 24 synthetic cases (data-derived expectations); floor
  gates all four numbers; recorded with `--record`.
- **Close** (spec 0034, PR #40): README/CHANGELOG reflect both verticals
  (incl. rolling Phase 2's lingering "Unreleased" entries into their
  section — drift repaired, noted); this entry; tag `phase-3`.

**Current eval numbers (recorded in eval/history.jsonl, schema v2)**
- **business — gold 7: faithfulness 1.000 (gated) · coverage 1.000 · quality 1.000;
  synthetic 52: 1.000 · 1.000 · 1.000.** (Unchanged through the refactor.)
- **devex — gold 7: faithfulness 1.000 (gated) · coverage 0.917 · quality 1.000;
  synthetic 24: 1.000 · 1.000 · 1.000.**
- The devex 0.917 is the **named** notif-svc on-call miss — planted in the
  corpus (spec 0026), predicted in the spec before the battery ran (spec
  0033), kept as the measured trigger for the next trust loop.

**Phase 3 milestone check (ROADMAP: "two genuinely different verticals run
on one unchanged core, both measured")**
- Same ingestion door ✓ (logs/diffs/tickets as EvidenceRecords; new locator
  kinds, zero engine change). RCA grounded in log lines + linked to prior
  incidents ✓. PR summaries tied to motivating tickets ✓. Eval extended ✓
  (own gold + synthetic, same floor). **Core unchanged — proven:**
  `git diff phase-2..HEAD` over the ADR 0008 frozen list
  (grounding/ingestion/graph/resolution/retrieval/routing/composition/
  reasoning/conflicts/knowledge/cli/salt/documents/eval-synthetic) is
  **empty**; the only core-adjacent diffs are the two sanctioned deltas
  (metrics: one generic shape; harness/history: battery parameterization).
  **Milestone met.** Tagged `phase-3`.

**Open questions / risks**
- **ADR 0003/0004 revisit triggers have now FIRED with a real measurement:**
  devex coverage 0.917 (vocabulary/variant mismatch the deterministic layer
  doesn't bridge). Decision recorded here rather than acted on mid-phase:
  evaluate the fix in Phase 4 — candidates are (a) deterministic alias
  support in the service catalog (additive, keeps clone-and-run; likely
  first), then (b) embeddings via SAP GenAI Hub with the lexical path as
  local fallback (the ADRs' stated end state). The miss is in the gold set,
  so any fix moves a public number.
- The business modules still live at `tessera/` top level while DevEx lives
  in `tessera/devex/` — recorded asymmetry (ADR 0008), scheduled for the
  Phase 4 relocation/polish.
- ADR 0007 trigger 2 (battery saturation) now applies per battery; the new
  devex battery is green on synthetic — watch in Phase 4.
- Confirm SAP AI Core / HANA Cloud access for Phase 4; not blocking.

**State of the tree**
- `main` green and in sync; no open branches. PRs #31–#40 merged. Tagged
  `phase-3`.

---

## 2026-06-10 — Phase 4 COMPLETE (autonomous run: platform, polish, and the story)

**Mode note:** ran **autonomously** end-to-end from one kickoff (per CLAUDE.md
"Autonomous phase execution"): eight units, each spec → branch → implement →
gate → PR → CI-green → squash-merge. The two project-shaping questions
(external services/spend) were **asked**, per the rules: the maintainer chose
*docs + tested seams, no provisioning* for the SAP path, and *GenAI Hub with
an Anthropic fallback* for the optional narration adapter.

**Done this session (8 units, PRs #41–#48)**
- **Phase plan** (spec 0035, PR #41): unit breakdown + the two asked
  decisions recorded before any code.
- **The coverage loop closed** (spec 0036, ADR 0010, PR #42): the FIRED
  ADR 0003/0004 triggers resolved deterministically — `components.csv`
  declares the `notif-svc` alias, the vertical asserts it as a reversible
  confidence-1.0 `Resolution`, and a new graph-aware **service route**
  answers ownership questions from the resolved entity. **Devex gold
  coverage 0.917 → 1.000** (recorded with `--record`); gold case 04
  strengthened (now also expects "Aiko Tanaka"). Embeddings reassessed and
  deferred with a refreshed trigger (a measured miss no declarable data
  could fix); `checkout-svc` (0.846) deliberately kept undeclared as the
  mechanism's visible boundary. Addenda on ADR 0003/0004.
- **Relocation** (spec 0037, PR #43): business answer layer →
  `tessera/business/` (cli, knowledge, composition, reasoning, conflicts,
  routing, synthetic), mirroring `tessera/devex/`; core `routing.py` keeps
  only the shared `Route` contract; entry points repointed, behaviour
  identical, numbers byte-identical. ADR 0008/0009 addenda close their
  recorded asymmetries.
- **Claim-grammar ownership** (spec 0038, ADR 0011, PR #44): the six
  business verifier shapes moved to `tessera/business/claims.py`, carried
  explicitly via `Battery.claim_shapes`; `eval/metrics.py` is now
  vertical-free (leak-guard test pins it); devex declares zero grammars —
  itself a generality data point. One deliberate precedence change
  (conclusion grammars own their verdict ahead of generic containment —
  stricter), measured to change nothing.
- **SAP deployment path** (spec 0039, ADR 0012, PR #45): `docs/DEPLOYMENT.md`
  (component→service mapping, env reference, provisioning runbook,
  verified-vs-not split) + `tessera/platform/` (config defaulting to local
  mode; `ModelProvider` protocol; GenAI Hub + Anthropic adapters in pure
  stdlib HTTP, contract-tested against fakes). No cloud touched; CI key-free.
- **The Joule-style session** (spec 0040, ADR 0013, PR #46):
  `uv run tessera-chat` over both verticals — explainable routing, numbered
  claims, `:show N` provenance exploration (records, locators, assertion
  trail with confidences, deduplicated), `:trust` panel from the history
  journal, a **live verifier check on every answer** (same `is_supported` +
  shapes as the eval), and optional narration under the ADR 0013 boundary
  (label below canonical claims; deterministic novelty guard discards
  fabricated numbers/ids with a notice; provider failure degrades silently;
  refusals never narrated).
- **The write-up** (spec 0041, PR #47): `docs/WRITEUP.md` — problem,
  architecture, how the metrics are earned, the recorded trail
  (business 0.929 → 0.938 → 1.000; devex 0.917 → 1.000), the empty-diff
  generality proof, limitations at full prominence, future work, reproduce
  commands.
- **Close** (spec 0042, PR #48): README stranger pass (current numbers, the
  chat door, DEPLOYMENT/WRITEUP links, gate = `scripts/gate.sh`, and one
  real **overclaim fixed** — agentic/MCP was asserted as present, now
  truthfully future work), CHANGELOG `[phase-4]` + repaired footer links,
  this entry, tag `phase-4`.

**Current eval numbers (recorded in eval/history.jsonl)**
- **business — gold 7: faithfulness 1.000 (gated) · coverage 1.000 · quality 1.000;
  synthetic 52: 1.000 · 1.000 · 1.000.**
- **devex — gold 7: faithfulness 1.000 (gated) · coverage 1.000 · quality 1.000;
  synthetic 24: 1.000 · 1.000 · 1.000.**
- Trend: business coverage 0.929 → 0.938 → 1.000; devex 0.917 → 1.000 —
  both loops closed metric-first, both recorded.

**Phase 4 milestone check (ROADMAP: "a senior engineer can clone, run, read,
and understand the project without the author in the room")**
- Clone-and-run: `uv sync` → all five doors run key-free; gate + eval green
  in CI ✓. Read: README → WRITEUP → DEPLOYMENT → ADR trail, all current and
  cross-linked ✓. SAP path: designed-for with runbook + tested seams (the
  honest posture SAP_ALIGNMENT endorses; provisioning deliberately declined) ✓.
  Joule-style surface with explorable provenance + visible trust signal ✓.
  Write-up with honest results and limitations ✓. **Milestone met.** Tagged
  `phase-4`.

**Open questions / risks**
- **ADR 0007 trigger 2 (battery saturation) is now true of both batteries** —
  every recorded number is 1.000. The next trust loop needs *harder* cases,
  not more green: free-form phrasing variety, multi-hop mixed-modality
  questions, scale. This is the named candidate for the next milestone's
  first unit.
- ADR 0010's refreshed embeddings trigger and ADR 0005's LLM-judge trigger
  are live and written down; neither has a measured case yet.
- The GenAI Hub adapter is contract-tested only; a provisioning session
  (runbook in DEPLOYMENT.md) would turn "designed for" into "ran on" in an
  afternoon — maintainer's call, spend involved.
- Conversation is stateless; follow-up context is named future work
  (WRITEUP).
- Roadmap note: the four ROADMAP phases are complete. What follows is
  post-roadmap work (next milestone to be defined with the maintainer —
  candidates: hardening loop on harder cases, real connectors, agentic/MCP
  mode, BTP provisioning, application/write-up packaging).

**State of the tree**
- `main` green and in sync; no open branches. PRs #41–#48 merged. Tagged
  `phase-4`.

---

## 2026-06-16 — Milestone 5 COMPLETE (post-roadmap hardening: the eval can fail again)

**Mode note:** ran **autonomously** end-to-end from one kickoff after a
project-shaping scope discussion (the maintainer chose: the hardening loop;
real connector + harder synthetic; hold the determinism line — pause before any
LLM/embedding). Eight units, each spec → branch → implement → gate → PR →
CI-green → squash-merge.

**The problem this milestone answers.** All four roadmap phases were done and
every recorded number was 1.000 — both synthetic batteries saturated (ADR 0007
trigger 2). A floor that cannot fail is decorative. And both prior coverage
recoveries closed misses the project *planted*. So the goal was inverted: make
the eval able to fail again with **un-planted** difficulty, faithfulness gated
at 1.0 throughout.

**Done this session (8 units, PRs #50–#57)**
- **Phase plan** (spec 0043, PR #50): unit breakdown + the three recorded
  scope decisions + the inverted success criterion.
- **The floor actually gates** (spec 0044, PR #51): `tessera-eval` wired into
  `scripts/gate.sh`, so the faithfulness floor's non-zero exit fails the build
  in CI, not only in the manual `/verify`. Proven by a forced breach. (The
  audit gap: the floor had been enforced by no automated gate.)
- **The first real connector** (spec 0045, ADR 0014, PR #52): the repo's own
  GitHub Actions history, ingested through the same door, reusing the table-row
  + log-span locator kinds with zero engine change (ADR 0002, 4th cash). Live
  fetch is a run-once script (the only network touchpoint); the snapshot is
  committed, scrubbed, byte-reproducible; logs ingested RAW (`##[error]`
  preserved). Separate graph → synthetic battery numbers byte-identical.
- **The measured un-planted miss + its close** (spec 0046, PR #53): a
  `github_actions` battery measured **gold coverage 0.000, quality 0.500**
  (real run-id + `##[error]` divergence the engine didn't bridge) — recorded on
  purpose, then closed additively (run-id grammar, `##[error]` marker, first
  `##[error]` line as signature) → **1.000**, with a genuine cross-run
  recurrence over two real Pages-deploy failures. Both points in
  `eval/history.jsonl`. **This is the milestone's core: the eval failed on data
  no one authored, then the trust loop closed it.**
- **Mixed-modality multi-hop in one turn** (spec 0047, PR #54): the Phase-2-named
  gap. RCA walks incident ticket → resolving PR → diff (`run → log → log →
  ticket → PR → diff`, each hop cited). Mis-pivot trap avoided structurally
  (PR-198 not PR-201). devex gold 7→8, all 1.000.
- **Free-form phrasing variety** (spec 0048, PR #55): router widened
  deterministically (synonyms; word-boundary matching fixing `most`⊂`almost`;
  currency-set validation fixing the `ASK`/`VAT` hijack — two latent bugs); the
  batteries now sample phrasing (business gold 7→9). Intent words left as the
  named ADR 0006 ceiling.
- **Scale, measured** (spec 0049, PR #56): a real-engine harness over 180
  entities — precision/recall hold, faithfulness holds, and the over-merge risk
  is now a *reproduced fact* (generic-suffix firms cross 0.85 at volume).
- **Trigger status + close** (spec 0050, this entry, PR #57): three committed
  specimens — ADR 0005 (verbatim-but-misleading passes the structural check),
  ADR 0010 (error-class synonymy no alias could bridge), ADR 0006 (intent-verb
  ceiling); WRITEUP hardening section + updated limitations; CHANGELOG; tag
  `milestone-5`.

**Current eval numbers (recorded in eval/history.jsonl)**
- **business — gold 9: 1.000 / 1.000 / 1.000; synthetic 52: 1.000 / 1.000 / 1.000.**
- **devex — gold 8: 1.000 / 1.000 / 1.000; synthetic 24: 1.000 / 1.000 / 1.000.**
- **github_actions (REAL) — gold 4: 1.000 / 1.000 / 1.000; synthetic 8: 1.000 / 1.000 / 1.000.**
- Trail: github_actions gold coverage **0.000 → 1.000**, quality **0.500 → 1.000**
  (the un-planted miss, deterministically closed). Verified under 5
  `PYTHONHASHSEED` values; 235 tests.

**Milestone check (the inverted criterion):** an un-planted, measured miss was
surfaced (real-data RCA) and closed deterministically; faithfulness stayed
gated at 1.0 throughout; the determinism line held (three triggers demonstrated
and escalated, none acted on); the WRITEUP's "scale untested" and "drop-in
shaped" claims are now tested/demonstrated. **Met.** Tagged `milestone-5`.

**Open questions / risks — the three live triggers, now with concrete specimens**
- **ADR 0010 (embeddings):** the error-class synonymy (`HttpError: Not Found` =
  `status: 404` = `Ensure GitHub Pages has been enabled`) is a real, present,
  *undeclarable* miss — the refreshed trigger's exact condition. Acting on it
  (GenAI Hub embeddings + HANA vector) needs spend/cloud — maintainer's call.
- **ADR 0005 (LLM-judge):** the verbatim-but-misleading specimen shows the
  structural blind spot; no *measured* case forces it yet.
- **ADR 0006 (semantic routing):** intent verbs (`rank`/`lead`/`best`) are the
  named ceiling; a correct refusal is the honest fallback.
- The over-merge at volume (ADR 0004) is now measured; multi-field ER or
  embeddings is the recorded remedy.

**Next milestone — to be defined with the maintainer.** Candidates: act on a
fired trigger (embeddings via GenAI Hub — the ADR 0010 specimen is ready, needs
spend); a second real connector (Jira/PR-and-issue export); agentic/MCP mode;
BTP provisioning (turn "designed for SAP" into "ran on SAP"); application
packaging for the SAP motivation letter.

**State of the tree**
- `main` green and in sync; no open branches. PRs #50–#57 merged. Tagged
  `milestone-5`.

---

## 2026-06-27 — Milestone 6 COMPLETE (embeddings on SAP: the synonymy miss closed, ran on SAP HANA)

**Mode note:** ran **autonomously** from one kickoff after a project-shaping
scope discussion. The maintainer chose: act on ADR 0010 (embeddings), the cloud
**"ran on SAP"** variant, keys available now. Mid-milestone the maintainer
**pivoted** GenAI Hub → HANA-native in-database embeddings (GenAI Hub deployment
was hard to configure); recorded in the ADR 0015 addendum. Nine units, each spec
→ branch → implement → gate → PR → CI-green → squash-merge.

**The problem this milestone answers.** Milestone 5 deliberately *kept* its
hardest specimen — the error-class synonymy in the real Pages-deploy log
(`HttpError: Not Found` ≈ `status: 404` ≈ `Ensure GitHub Pages has been enabled`),
a measured miss no declared catalog data could fix (ADR 0010's exact firing
condition). M6 closes it — **with real semantic embeddings, on real SAP HANA
Cloud** — the inverse of M5's "keep the miss".

**Done this session (9 units, PRs #61–#68)**
- **Phase plan** (spec 0051, #61) + the two recorded scope decisions.
- **Embedding-provider seam** (spec 0052, ADR 0015, #62): `EmbeddingProvider` +
  GenAI Hub adapter (stdlib HTTPS, fake-transport contract tests); `TESSERA_EMBEDDINGS`
  selector.
- **Vector-store seam** (spec 0053, #63): `VectorStore` + in-memory + HANA
  (`REAL_VECTOR`/`COSINE_SIMILARITY`); `hdbcli` opt-in `cloud` extra, lazy import;
  a test pins the default import graph has no `hdbcli`.
- **Semantic retrieval + leak-guard** (spec 0054, #64): `tessera/semantic.py`;
  lexical BM25 fallback; subprocess leak-guard pins the verifier imports no
  embedding module (faithfulness stays structural).
- **HANA-native embeddings — the pivot** (spec 0055, ADR 0015 addendum, #65):
  `HanaSemanticIndex` embeds in-SQL via `VECTOR_EMBEDDING` (vectors never enter
  Python); GenAI Hub path kept as the documented alternative.
- **Eval cloud-mode + the synonymy gold case** (spec 0056, #66): harness builds
  the index per battery; `github_actions/05` is a lexical miss recorded at gold
  coverage **0.833**; precision guard (positively-aligned records only).
- **Deployment runbook + `.env.example`** (spec 0057, #67): NLP feature,
  least-privilege user, smoke test, one-shot record.
- **THE online measurement** (spec 0058, #68): ran it on SAP HANA Cloud —
  in-database `VECTOR_EMBEDDING` (`SAP_NEB.20240715`, 768-dim) + `COSINE_SIMILARITY`
  closed the case to **coverage 1.000, quality 1.000**, faithfulness 1.0;
  recorded in `eval/history.jsonl`. Fixed two real issues the live run surfaced
  (existence-check casing; the gold case expected the diluted log chunk rather
  than the run-status row semantics actually surfaces).
- **Close** (spec 0059, this entry): WRITEUP "embeddings on SAP" section +
  updated limitations; README numbers (offline 0.833 + the SAP close explained);
  CHANGELOG `[milestone-6]`; verified under 4 `PYTHONHASHSEED` values; tag
  `milestone-6`; memory.

**Current eval numbers (recorded in eval/history.jsonl)**
- **business — gold 9: 1.000 / 1.000 / 1.000; synthetic 52: all 1.000.**
- **devex — gold 8: 1.000 / 1.000 / 1.000; synthetic 24: all 1.000.**
- **github_actions — gold 5: faithfulness 1.000, coverage 0.833 (offline) /
  1.000 (online HANA), quality 0.800 / 1.000; synthetic 8: all 1.000.**
- Trail: github_actions gold synonymy case **0.833 (lexical/offline) → 1.000
  (HANA embeddings/online)** — the trust-loop pair, both points recorded.
  Verified deterministic across `PYTHONHASHSEED` 0/1/42/2026; 263 tests.

**Milestone check:** a previously-recorded, named miss was closed by a real
method upgrade (embeddings), **measured on cloud infrastructure** ("ran on SAP");
faithfulness stayed gated at 1.0; embeddings are retrieval-only and the verifier
stayed embedding-free (leak-guard); CI stays offline/lexical/key-free. **Met.**
Tagged `milestone-6`.

**Open questions / risks**
- The online embedding number is a **timestamped measurement, not
  CI-reproducible** (cloud model can change); CI's public number is the lexical
  0.833. Documented in README/WRITEUP/DEPLOYMENT.
- **Long-document dilution** is a named limitation: SAP's embedding bridges the
  concept but the concise run-status row outranks the long error-log chunk;
  finer log chunking would let the specific 404 line surface.
- Embeddings are **retrieval-only**; applying them to ER (the `checkout-svc` /
  over-merge cases) is the additive next step. ADR 0005 (LLM-judge) and ADR 0006
  (semantic routing) triggers remain live and unacted.
- A `TESSERA.TESSERA_DOC_VECTORS` table (8 rows) exists on the HANA instance; the
  eval re-upserts idempotently. The recorded run used `DBADMIN`; the documented
  least-privilege `TESSERA_APP` user is the recommended production setup.

**Next milestone — to be defined with the maintainer.** Candidates: embedding-
assisted ER + finer log chunking (the natural M6 follow-through); a second real
connector (Jira / PR-and-issue export); agentic / MCP-exposed grounded mode; full
HANA graph persistence; BTP serving (container → AI Core/Kyma).

**State of the tree**
- `main` green and in sync; no open branches. PRs #61–#68 merged. Tagged
  `milestone-6`.

---

## 2026-06-27 — Milestone 7 COMPLETE (embeddings beyond retrieval: ER + de-diluted logs, ran on SAP)

**Mode note:** ran **autonomously** from one kickoff after a project-shaping scope
discussion. The maintainer chose (asked 2026-06-27): act on both M6-named
limitations — embedding-assisted ER + finer log chunking; ER scope = close
checkout-svc recall **and** attempt the generic-suffix over-merge, recording the
residual honestly; online HANA re-measurement **yes**. Eight units, each spec →
branch → implement → gate → PR → CI-green → squash-merge.

**The problem this milestone answers.** Milestone 6 confined embeddings to
retrieval and named two limitations: ER had never seen an embedding (the
undeclared `checkout-svc` 0.846 recall miss; the generic-suffix over-merge), and
long error-logs diluted (the 404 line buried under provisioning boilerplate, so
the synonymy answer surfaced the run, not the line). M7 acts on both — and runs it
on SAP.

**Done this session (8 units, PRs #70–#77)**
- **Phase plan** (spec 0060, #70) + the three recorded scope decisions.
- **ER embedding seam** (spec 0061, ADR 0016, #71): `tessera/er_semantic.py` —
  a second additive regime that proposes merges from the cosine of the two names'
  **distinctive stems** (name minus generic tokens). One stem-gated rule resolves
  the opposite-direction tension; retrieval/link-only, leak-guard extended. Stub
  mechanism proof.
- **ER precision/recall, measured** (spec 0062, #72): a labeled pair-set —
  `difflib` 0.50/0.50 vs stem-embedding 1.00/1.00; reported, not gated. The honest
  residual asserted: the union's precision gap is *entirely* `difflib`'s existing
  over-merge (additive can't remove it).
- **Applied to the devex graph** (spec 0063, #73): vertical-side, behind
  `TESSERA_EMBEDDINGS`; none-path byte-identical; stub-proven close (checkout-svc
  resolves; precision held; reversible; faithful). HANA-native `via_index`
  proposer for the online path.
- **Finer log chunking** (spec 0064, ADR 0017, #74): `parse_log_chunks` isolates
  the `##[error]` cluster (3-line context window keeps ruff's "Would reformat"
  attached); stable role-tagged ids (`chunk{n}`/`error{n}`); gold-01/02 re-pointed;
  RCA unchanged; offline numbers byte-identical.
- **Eval cloud-mode** (spec 0065, #75): the devex on-call gold case 09 (offline
  miss → devex gold 0.950/0.889) + de-diluted gold-05 re-point; offline-miss
  recorded.
- **The online measurement — RAN ON SAP** (spec 0066, #76 prep + #77 record): the
  HANA smoke test surfaced that HANA embeddings are **asymmetric** (`QUERY`/
  `DOCUMENT`, identical text ≈ 0.889); one `TESSERA_EMBEDDINGS=hana` one-shot
  closed **both** misses online — devex gold 0.950→1.000, github_actions gold
  0.833→1.000, faithfulness 1.0 — recorded in `eval/history.jsonl`. Earned, not a
  re-saturation: distinct services did **not** over-merge online (cross-service
  stem cosines 0.49–0.58 < 0.85; only the four catalog↔on-call matches fired).
- **Close** (spec 0067, this entry): WRITEUP M7 section + updated limitations/
  future-work; README numbers (devex 0.950, github_actions 0.833, both closes
  explained); CHANGELOG `[milestone-7]`; empty-diff core check (clean); verified
  under `PYTHONHASHSEED` 0/1/2026; tag `milestone-7`; memory.

**Current eval numbers (recorded in eval/history.jsonl)**
- **business — gold 9: 1.000 / 1.000 / 1.000; synthetic 52: all 1.000.**
- **devex — gold 9: faithfulness 1.000, coverage 0.950 (offline) / 1.000 (online
  HANA), quality 0.889 / 1.000; synthetic 24: all 1.000.**
- **github_actions — gold 5: faithfulness 1.000, coverage 0.833 (offline) / 1.000
  (online HANA), quality 0.800 / 1.000; synthetic 8: all 1.000.**
- Two trust-loop pairs recorded: devex checkout-svc **0.950 → 1.000** (embedding
  ER) and github_actions synonymy **0.833 → 1.000** (de-diluted log + embeddings),
  both online points timestamped, both offline misses kept in CI. Engine core
  unchanged (empty-diff over the ADR 0008 frozen list, milestone-6..HEAD).

**Milestone check:** both M6-named limitations closed by a method upgrade,
**measured on SAP HANA**; faithfulness gated 1.0 throughout; embeddings stayed
link-only and the verifier embedding-free (leak-guard incl. the ER module); the
close is earned (no online over-merge) and the unfixable residual (the additive
regime can't cure `difflib`'s over-merge) is recorded with its next lever
(stem-gate the `difflib` pass / multi-field ER). **Met.** Tagged `milestone-7`.

**Open questions / risks**
- The online numbers are **timestamped, not CI-reproducible** (the cloud model can
  change; HANA embeddings are asymmetric). CI's public numbers stay the offline
  misses (devex 0.950, github_actions 0.833).
- **The generic-suffix over-merge residual** stands: an additive embedding regime
  can't remove a `difflib` false positive. Stem-gating the `difflib` pass (a
  deterministic change altering `resolve_entities`/`test_scale`) or multi-field ER
  is the named, measured next lever.
- ADR 0005 (LLM-judge) and ADR 0006 (semantic routing) triggers remain live and
  unacted; no measured case forces either.
- A `TESSERA.TESSERA_ER_VECTORS` table now exists on the HANA instance alongside
  `TESSERA_DOC_VECTORS`; the eval re-upserts idempotently. The run used the `.env`
  credentials present from M6.

**Next milestone — to be defined with the maintainer.** Candidates: cure the
generic-suffix over-merge (stem-gate the `difflib` pass, or multi-field ER — the
recorded next lever); a second real connector (Jira / PR-and-issue export);
agentic / MCP-exposed grounded mode; full HANA graph persistence; BTP serving.

**State of the tree**
- `main` green and in sync; no open branches. PRs #70–#77 merged. Tagged
  `milestone-7`.

---

## 2026-06-28 — Milestone 8 COMPLETE (cure the generic-suffix over-merge: stem-gated deterministic ER)

**Mode note:** ran **autonomously** from one kickoff after a project-shaping scope
discussion. The maintainer chose (asked 2026-06-28): **(1) lever scope** — stem-gate
the deterministic `difflib` pass only (not multi-field ER); **(2) honesty posture** —
keep a new measured edge rather than claim the over-merge universally solved. Four
units, each spec → branch → implement → gate → PR → CI-green → squash-merge. Fully
**offline / CI-reproducible — no cloud, no online run** (the inverse of M6–7).

**The problem this milestone answers.** Milestone 7's embedding ER regime was
*additive*, so it closed `checkout-svc` recall but could not remove the deterministic
pass's pre-existing **generic-suffix over-merge** (distinct firms sharing
`… Logistik GmbH` collapse because the shared suffix dominates the `difflib` ratio;
measured in `tests/test_scale.py`, difflib precision 0.50 / union 0.67 in
`tests/test_er_metrics.py`). The recorded next lever was to stem-gate the `difflib`
pass itself — a deterministic engine change. M8 takes it.

**Done this session (4 units, PRs #79–#81 + this close)**
- **Phase plan** (spec 0068, #79) + the two recorded scope decisions.
- **Relocate the stem helpers** (spec 0069, #80): `tokenize`/`generic_tokens`/
  `distinctive_stem`/`ORG_DESCRIPTORS`/`DEFAULT_MIN_GENERIC_DF` moved from
  `er_semantic.py` (leak-guard-banned) to the embedding-free `resolution.py`, so the
  engine's deterministic pass can share them without pulling an embedding import
  toward the verifier. `er_semantic` re-exports; behaviour byte-identical.
- **Stem-gate `resolve_entities` + ADR 0018** (spec 0070, #81): a `difflib` match
  ≥ 0.85 is confirmed only on a shared **distinctive (non-generic) signal** — a
  non-generic token, a near-identical distinctive stem, or a ≤ 2 edit distance.
  Genericness is **corpus-derived** (a token is generic iff ≥ 3 of the names
  containing it stay dissimilar once it AND the known generics are removed — iterated
  to a **fixpoint** so multi-token suffixes are caught), avoiding the
  document-frequency trap that would mis-strip `Bayerische` (one firm's duplicate
  records). Single-character tokens (`G.m.b.H` → `g m b h`) are dropped so a
  punctuated legal form never pollutes a stem.
- **Close** (spec 0071, this entry): WRITEUP M8 section + updated limitations/
  future-work + a sixth "what was learned"; README ER section + Status prose +
  ADR 0018 link; CHANGELOG `[milestone-8]`; ADR nav/index; frozen-core check; tag
  `milestone-8`; memory; kickoff.

**The honest engineering story (recorded in ADR 0018 + the WRITEUP).** The first,
simpler gate (compare bare distinctive stems) was **measured against the real demo
graph** and found to veto genuine typo merges (`Maple eLaf`/`Maple Leaf`) — stripping
shared context amplifies a one-token typo. An **adversarial multi-agent review**
(5 lenses, worktree) then surfaced three confirmed majors: a short-head-typo recall
regression (`Stein`/`Stien`), a multi-token-suffix hole (`Trade Logistik GmbH`), and
doc over-claims. All three were fixed (edit-distance fallback, genericness fixpoint,
single-char filter, honest wording) and each is now pinned by a regression test.

**Current eval numbers (unchanged from M7 — the cure is precision-only, offline):**
- **business — gold 9: 1.000 / 1.000 / 1.000; synthetic 52: all 1.000.**
- **devex — gold 9: faithfulness 1.000, coverage 0.950 (offline) / 1.000 (online
  HANA, M7), quality 0.889 / 1.000; synthetic 24: all 1.000.**
- **github_actions — gold 5: faithfulness 1.000, coverage 0.833 / 1.000 (online,
  M7), quality 0.800 / 1.000; synthetic 8: all 1.000.**
- **ER precision (reported, not gated, `tests/test_er_metrics.py`): `difflib`
  0.50 → 1.000, union 0.67 → 1.000.** Business + devex **resolved cluster signatures
  byte-identical** before/after the gate (hashed vs pre-gate `main`); deterministic
  across `PYTHONHASHSEED` 0/1/42/2026. 299 tests.

**Milestone check:** the generic-suffix over-merge is cured in the core deterministic
pass, **provably in CI** (no online run); difflib/union precision moved to 1.0; no
resolved cluster changed (measured); faithfulness gated at 1.0; the leak-guard holds
(the cure is embedding-free, stem helpers in `resolution.py`); and three residuals
are kept as measured edges pointing at multi-field ER. **Met.** Tagged `milestone-8`.

**Open questions / risks**
- **The frozen core changed for the first time** since Phase 3 (ADR 0008): `graph.py`
  + `resolution.py`, the one sanctioned M8 delta (a general ER precision improvement
  belongs in core). Everything else in the frozen list stays empty-diff
  (`milestone-7..HEAD` verified). Future milestones should keep treating a core
  change as ADR-worthy.
- **Recorded residuals (multi-field ER is the lever):** character-identical distinct
  firms; two-firm (`< min_df`) suffix collisions; a double-typo pair with no cleaner
  co-referent (rescued by transitivity on the demo data, not in general). Each pinned
  by a test.
- ADR 0005 (LLM-judge) and ADR 0006 (semantic routing) triggers remain live and
  unacted; no measured case forces either.
- The M6/M7 online HANA numbers remain timestamped, not CI-reproducible; CI's public
  numbers stay the offline misses (devex 0.950, github_actions 0.833). M8 added no
  online number.

**Next milestone — to be defined with the maintainer.** Readiest candidates:
**multi-field ER** (name + address + keys — the recorded next lever, would resolve
all three M8 residuals and is fully offline); a second real connector (Jira /
PR-and-issue export); agentic / MCP-exposed grounded mode; full HANA graph
persistence; BTP serving.

**State of the tree**
- `main` green and in sync; no open branches. PRs #79–#81 merged. Tagged
  `milestone-8`.

---

## 2026-06-28 — Milestone 9 COMPLETE (multi-field entity resolution: name + address)

**Mode note:** ran **autonomously** from one kickoff after a project-shaping scope
discussion. The maintainer chose (asked 2026-06-28): **(a)** match on name + address
(no new key column — address already lives in the graph as `has_address` edges);
**(b)** combine via a **two-way deterministic gate** (address disagreement vetoes an
over-merge, agreement bridges a corroborated near-match — a hard gate, since clusters
are connected components and confidence can't change membership); **(c)** add a
same-name/different-address pair so the fix is a **measured before/after**. Five units,
each spec → branch → implement → gate → PR → CI-green → squash-merge. Fully **offline /
CI-reproducible — no embedding, no cloud** (the same posture as M8).

**The problem this milestone answers.** Milestone 8 cured the generic-suffix over-merge
but left three residuals, each pinned by a test, all naming the **same** next lever:
name-only ER cannot split two distinct firms with the *same* name, nor a two-firm
suffix collision below the genericness floor, nor rescue a double-typo pair whose
tokens are both misspelled. ADR 0004 had named multi-field matching (name + address)
"an additive extension, not a redesign." M9 takes it.

**Done this session (5 units, PRs #83–#86 + this close)**
- **Phase plan** (spec 0072, #83) + the three recorded scope decisions.
- **Multi-field engine + ADR 0019** (spec 0073, #84): `resolve_entities` gains an
  optional ordered `match_fields`; `resolution.compare_match_fields` (pure-stdlib,
  embedding-free) yields an agree/contradict/neutral address signal; `graph._merge_reason`
  folds it into the M8 stem-gate decision as a **two-way gate** (veto an over-merge,
  bridge a double-typo). Default `()` is byte-identical to M8 (none-path).
  A **pre-merge 5-lens adversarial review** confirmed **7 of 9** findings — the
  headline a root-cause major (a `difflib` ratio scores `D-20095` ~ `20095` at 0.909,
  a false postal AGREE that breaks the veto arm); **fixed** with **exact normalized
  equality** (`normalize` still folds umlauts, so a city's variants agree) + the
  byte-exact none-path pin, the 6th truth-table-cell test, and code-honest
  corroboration wording.
- **Business wiring, no regression measured** (spec 0074, #85): `sources/salt.py`
  emits the address signature (`postal_code` + `city_name`) on customer + address
  nodes; `build_demo_graph` opts in. The business resolved clusters are **byte-identical
  with and without** `match_fields` (308 both ways) — proven, not assumed; the
  corroboration arm adds exactly one assertion (the Noridc/Nordic Timbre double-typo
  pair now bridges directly, residual 3 on the real graph).
- **The disambiguation pair + the measured close** (spec 0075, #86): two distinct
  "Hanseatic Trading GmbH" firms at different addresses (Hamburg / Munich), appended
  outside the RNG stream (existing rows byte-identical). New gold case (kind=refuse):
  name-only ER over-merges and wrongly **answers** the ambiguous-name question
  (**business gold quality 0.900**); multi-field ER splits the firms and correctly
  **refuses** (**1.000**) — both points in `eval/history.jsonl`
  (`scripts/record_m9_close.py`), faithfulness 1.0 throughout, **CI-reproducible**.
- **Close** (spec 0076, this entry): WRITEUP M9 section + updated limitations/
  future-work + a seventh "what was learned"; README ER section + numbers; CHANGELOG
  `[milestone-9]`; ADR nav/index; frozen-core check; tag `milestone-9`; memory; kickoff.

**Current eval numbers (recorded in eval/history.jsonl)**
- **business — gold 10: faithfulness 1.000, coverage 1.000, quality 1.000 (multi-field)
  / 0.900 (name-only baseline, the recorded miss); synthetic 53: all 1.000.**
- **devex — gold 9: faithfulness 1.000, coverage 0.950 (offline) / 1.000 (online HANA,
  M7), quality 0.889 / 1.000; synthetic 24: all 1.000.**
- **github_actions — gold 5: faithfulness 1.000, coverage 0.833 / 1.000 (online, M7),
  quality 0.800 / 1.000; synthetic 8: all 1.000.**
- Trust-loop pair recorded: business gold quality **0.900 (name-only) → 1.000
  (multi-field)** — the ambiguous-name miss, closed offline and CI-reproducibly (unlike
  the M6/M7 online closes). Deterministic across `PYTHONHASHSEED` 0/1/42/2026.

**Milestone check:** the three M8 residuals are closed by a second deterministic
signal (the address), **provably in CI**; the over-merge → split is a measured eval
before/after; faithfulness stayed gated at 1.0; the leak-guard holds (the gate is
embedding-free in `resolution.py`); the business/devex clusters are unchanged except
the one intended Hanseatic split (pinned); and a new measured edge is kept (same name
**and** same address → a registration/tax key is the next lever). **Met.** Tagged
`milestone-9`.

**Open questions / risks**
- **Frozen core touched again** (ADR 0008): the sanctioned `milestone-8..HEAD` deltas
  are three frozen-list files — `graph.py` + `resolution.py` (the general engine gate)
  and `sources/salt.py` (the source's additive address attributes; schema knowledge
  stays in the source). Everything else empty-diff, the verifier included (ADR 0019).
- **Postal-anchored, not postal-perfect.** Field agreement is exact normalized
  equality; a genuine same-firm pair whose records carried *different* postals would be
  wrongly split (absent from the synthetic data, where postal is the canonical value).
  The corroboration arm's residual precision risk (two distinct firms, name-similar +
  same exact address) is a recorded measured edge, not a code guarantee (ADR 0019).
- **The remaining ER floor:** two distinct firms with the same name **and** the same
  address — only a registration/tax key separates them, the named next lever.
- ADR 0005 (LLM-judge) and ADR 0006 (semantic routing) triggers remain live and
  unacted; no measured case forces either. The M6/M7 online HANA numbers remain
  timestamped, not CI-reproducible; M9 added no online number.

**Next milestone — to be defined with the maintainer.** Readiest candidates:
**registration/tax-key matching** (the recorded next lever — a new exact-match field
into the same assertion layer, resolves the last ER floor, fully offline); a second
real connector (Jira / PR-and-issue export); agentic / MCP-exposed grounded mode; full
HANA graph persistence; BTP serving.

**State of the tree**
- `main` green and in sync; no open branches. PRs #83–#86 merged. Tagged
  `milestone-9`.

---

## 2026-06-28 — Milestone 10 COMPLETE (registration-key entity resolution)

**Mode note:** ran **autonomously** from one kickoff after a project-shaping scope
discussion. The maintainer chose (asked 2026-06-28): **(a)** `VATRegistration` on
**every** customer, per legal entity (realistic master data; clusters proven
byte-identical); **(b)** field = `VATRegistration` (a real S/4HANA `I_Customer`
field). I recommended and the maintainer accepted: the key as the **first
`match_field`** reusing the existing Milestone-9 exact-equality gate — **no engine
logic change**. Four units, each spec → branch → implement → gate → PR → CI-green →
squash-merge. Fully **offline / CI-reproducible — no embedding, no cloud** (the M8/M9
posture).

**The problem this milestone answers.** Milestone 9 made ER multi-field (name +
address) but left one floor, pinned by a test and recorded in ADR 0019: two genuinely
distinct firms with the **same** name **and** the **same** address. The address
*agrees*, so it corroborates a merge and the firms over-merge — only an exact identity
key separates them. The recorded M9 next lever. M10 takes it.

**The headline finding.** The M9 engine already supported it. `compare_match_fields`
was already ordered / exact-equality / first-present-decides, and the two-way gate
already vetoed on CONTRADICT and bridged on AGREE for *whatever* field led
`match_fields`. A registration key **is** an exact-equality field, so it slots in as
the **first** entry: `CUSTOMER_MATCH_FIELDS = ("vat_registration", "postal_code",
"city_name")`. So M10 touched only the business source (additive attr + ordering), the
data, the eval, and tests. **`resolution.py` empty-diff; `graph.py`'s only behavioural
change is a one-line honesty wording generalization** (the bridge reason said "bridged
by address", which under a key-led tuple misreports the field → "bridged by
corroborating field"; `signal.detail` names the actual field). The smallest of the
three frozen-core deltas.

**Done this session (4 units, PRs #88–#90 + this close)**
- **Phase plan** (spec 0077, #88) + the two recorded scope decisions + the
  zero-engine-change finding.
- **VATRegistration field + source wiring + ADR 0020** (spec 0078, #89): the column
  (per-entity, all customers, distinct VATs for the same-name Hanseatic pair, a
  collision guard); `vat_registration` on the customer node + **denormalized onto its
  address node** (a shared/serviced-office address carries none — absence is never a
  contradiction); `build_demo_graph` defaults to the key-first tuple. Proofs:
  vat-first clusters byte-identical to the M9 address-only path on existing data; the
  key decides above postal (retiring M9's postal-anchored cost); same-key merges,
  different-key splits. **Pre-merge 5-lens adversarial review (8 agents): 3 findings,
  0 majors, all fixed** — a real-SALT-safe denormalization guard and finishing the
  graph.py "address" → field-general wording.
- **The same-name/SAME-address pair + the measured close** (spec 0079, #90): two
  distinct "Havel Kontor GmbH" firms at one address (distinct AddressIDs, distinct
  VATs, no orders); existing rows byte-identical. New gold case 11 (kind=refuse):
  name + address ER over-merges → **answers** (business gold quality 0.909); the key
  splits → **refuses** (1.000) — both points in `eval/history.jsonl`
  (`scripts/record_m10_close.py`), faithfulness 1.0, CI-reproducible. The new floor
  (same name + address + key) pinned. **Honest disclosure:** adding 4 short records
  shifted BM25 `avgdl` and flipped a 0.05% near-tie in an unrelated retrieval test (a
  section heading vs its first clause, both surfaced top from the MSA with doc-span
  provenance); the test now pins the robust top-2 invariant and the heading-chunk root
  cause is filed as retrieval future work. The eval floor was untouched at 1.0.
- **Close** (spec 0080, this entry): WRITEUP M10 section + limitations/future-work +
  an 8th "what was learned"; README ER section + numbers; CHANGELOG `[milestone-10]`;
  ADR 0020 nav/index; frozen-core empty-diff audit; tag `milestone-10`; memory; kickoff.

**Current eval numbers (recorded in eval/history.jsonl)**
- **business — gold 11: faithfulness 1.000, coverage 1.000, quality 1.000 (key) / 0.909
  (M9 address-only baseline, the recorded miss); synthetic 53: all 1.000.**
- **devex — gold 9: faithfulness 1.000, coverage 0.950 (offline) / 1.000 (online HANA,
  M7), quality 0.889 / 1.000; synthetic 24: all 1.000.**
- **github_actions — gold 5: faithfulness 1.000, coverage 0.833 / 1.000 (online, M7),
  quality 0.800 / 1.000; synthetic 8: all 1.000.**
- Trust-loop pair recorded: business gold quality **0.909 (M9 address-only) → 1.000
  (M10 registration key)** — the same-address ambiguous-name miss, closed offline and
  CI-reproducibly. Deterministic across `PYTHONHASHSEED` 0/1/42/2026; 322 tests.

**Milestone check:** the last name+address ER floor (same name + same address, distinct
firms) is closed by an exact registration key, **provably in CI**; the over-merge →
split is a measured eval before/after; faithfulness stayed gated at 1.0; the leak-guard
holds (`resolution.py` empty-diff); the business/devex clusters are unchanged except the
one intended Havel split (pinned); the engine logic is unchanged (only a one-line
honesty wording delta in `graph.py`); and a new measured edge is kept (same name AND
address AND key → only an external registry separates). **Met.** Tagged `milestone-10`.

**Open questions / risks**
- **Frozen core touched minimally** (ADR 0008): the `milestone-9..HEAD` engine delta is
  `graph.py` alone (the bridge-wording generalization — behaviour-preserving;
  `resolution.py` empty-diff). The source delta (`sources/salt.py`, additive key attr +
  denormalization + ordering) is the sanctioned vertical-source change (ADR 0011/0020).
- **The remaining ER floor (registry-only):** two distinct firms with the same name
  **and** the same address **and** the same key are indistinguishable from the signals
  in the data — only an external registry / human adjudication separates them.
- **A retrieval fragility surfaced and was recorded:** a Markdown section heading
  competes with its content in BM25 (a near-tie flipped by corpus size). Filed as a
  follow-up task; the renewal test now pins the robust invariant; the eval is untouched.
- ADR 0005 (LLM-judge) and ADR 0006 (semantic routing) triggers remain live and unacted;
  no measured case forces either. The M6/M7 online HANA numbers remain timestamped, not
  CI-reproducible; M10 added no online number.

**Next milestone — to be defined with the maintainer.** Readiest candidates: the
**heading-chunk retrieval fix** (the surfaced fragility — a focused retrieval/chunking
improvement); a second real connector (Jira / PR-and-issue export); agentic / MCP-exposed
grounded mode; full HANA graph persistence; BTP serving. The ER lever is now largely
spent — the residual floor is registry-only, not a heuristic gap.

**State of the tree**
- `main` green and in sync; no open branches. PRs #88–#90 merged. Tagged
  `milestone-10`.

---

## 2026-06-28 — Milestone 11 COMPLETE (agentic / MCP-exposed grounded mode)

**Mode note:** ran **autonomously** from one kickoff after a project-shaping scope
discussion. The maintainer chose (asked 2026-06-28): **(1) thrust** — agentic /
MCP-exposed grounded mode (over a second connector / HANA persistence / BTP serving);
**(2) posture** — deterministic, offline, CI-reproducible (no LLM on the trust path,
no cloud, no spend); **(3) surface scope** — read-only grounded tools (no effectful
actions or proposals). Six units, each spec → branch → implement → gate → PR →
CI-green → squash-merge. Fully **offline / CI-reproducible** (the M8–M10 posture); the
MCP SDK rides as an opt-in extra, so CI stays pure-stdlib.

**The problem this milestone answers.** The project's thesis is "a trust layer for
**enterprise AI agents**," but through ten milestones Tessera only ever answered a
*human*. The Phase-4 close even removed an overclaim that asserted agentic/MCP was
present, recording it as future work. The ER lever was spent (M10's residual is
registry-only), so M11 opens a **new dimension**: let an agent consume Tessera as its
grounded substrate, and prove the trust contract survives the protocol.

**Done this session (6 units, PRs #92–#96 + this close)**
- **Phase plan** (spec 0081, #92) + the three recorded scope decisions.
- **Heading-chunk retrieval fix** (spec 0082, ADR 0021, #93): the folded-in M10
  fragility. `ingestion.chunk_text` merges a pure ATX-heading block (`^#{1,6}[ \t]+\S`
  — never `##[error]`) into the content it introduces, so a heading no longer competes
  in BM25 with its own clause; the renewal clause is a stable rank-1 again (18.54 vs
  12.08) and the renewal test is restored to a **strict** top-1 assertion. Gold
  01/03/07 + test_conflicts re-pointed; devex/github numbers **byte-identical**.
  **Pre-merge 5-lens adversarial review** (frozen-core change): 4 clean, 1 minor caught
  — the merge re-joined text with a single blank, which under multi-blank gaps would
  make the cited line range over-claim the backing lines; fixed by reconstructing from
  the **verbatim source span** and pinned by a contiguity invariant.
- **Grounded-tool layer** (spec 0083, ADR 0022, #94): `src/tessera/agent/` —
  `ground(domain, question)` over all three domains (business, devex, real
  github_actions; the devex router applies unchanged over the snapshot), each claim
  **live-verified at the boundary** with the eval's own `is_supported`, returning a
  JSON-serializable `GroundedResult` (route, claims with per-claim verdict + full
  provenance inline, refusal carried explicitly). A second tool `assertions` surfaces
  the reversible ER trail. `ChatSession` refactored to share the registry + verify loop
  (behaviour byte-identical; test_surface unchanged). Leak-guard extended (the layer
  pulls no embedding/LLM/`hdbcli`/`mcp` import; `platform.providers` is the documented
  inert transitive exclusion).
- **MCP server** (spec 0084, #95): `tessera-mcp`, a thin transport (no grounding logic)
  over the SDK's stdio transport. SDK = opt-in `agent` extra; default graph + CI never
  import `mcp` (subprocess pin; `uv sync --frozen` base; mypy `mcp.*` ignore +
  per-module untyped-decorator relaxation so the gate is green with or without the
  extra). A **real MCP client↔server session** captured to `data/mcp_session/`
  (TRANSCRIPT.md + session.json): grounded answer per domain, a refusal carried as a
  refusal, the ER trail — every claim `verified=true`. Also made the boundary output
  deterministic across hash seeds (sort a claim's support by id; the recorder surfaced
  the seed-dependent set order).
- **Trust across the boundary** (spec 0085, #96): extracted `serialize_answer` (the one
  `Answer → GroundedResult` projection) and added `tests/test_boundary.py`, the
  recorded CI-gated measurement over **every gold case in all three batteries**: the
  projection is **lossless** (same claims/support/verdicts as the engine `Answer`) and
  **faithfulness is 1.0 across the boundary**. Two honest router-vs-engine divergences
  pinned + explained (below).
- **Close** (spec 0086, this entry): frozen-core empty-diff audit; WRITEUP M11 section
  + limitations/future-work + a 9th "what was learned"; README (the agent/MCP door, the
  reverse-overclaim fixed, stale gold count 10→11); CHANGELOG `[milestone-11]`; ADR
  0021/0022 nav + index; STATUS; tag `milestone-11`; memory; kickoff.

**Current eval numbers (unchanged — the agent layer is a consumer, not a new path)**
- **business — gold 11: 1.000 / 1.000 / 1.000; synthetic 53: all 1.000.**
- **devex — gold 9: faithfulness 1.000, coverage 0.950 (offline) / 1.000 (online HANA,
  M7), quality 0.889 / 1.000; synthetic 24: all 1.000.**
- **github_actions — gold 5: faithfulness 1.000, coverage 0.833 / 1.000 (online, M7),
  quality 0.800 / 1.000; synthetic 8: all 1.000.**
- **New, recorded and gated in CI: faithfulness is 1.0 *across the MCP boundary*** over
  every gold case (`tests/test_boundary.py`), and the boundary projection is lossless.
  Deterministic across `PYTHONHASHSEED` 0/1/42/2026; **348 tests pass, 2 contract
  tests skip** without the `agent` extra (350 collected).

**Milestone check:** an enterprise AI agent can call Tessera over MCP and receive
grounded, cited, verifier-checked answers and principled refusals for both verticals
and the real connector; the trust contract is **measured** to survive the protocol
boundary (faithfulness 1.0, lossless projection, refusals preserved); the MCP SDK is
opt-in and CI stays pure-stdlib; the verifier is empty-diff and the leak-guard holds;
the one sanctioned frozen-core delta (the heading-chunk fix, ADR 0021) retired the M10
fragility. **Met.** Tagged `milestone-11`.

**Open questions / risks**
- **Frozen core touched once** (ADR 0008): `ingestion.py` (`chunk_text`, ADR
  0021-sanctioned) is the only frozen-list delta `milestone-10..HEAD`; `eval/metrics.py`
  (verifier), `graph.py`, `resolution.py`, and the rest are empty-diff (per-file
  audited). The agent layer + MCP server are new; `surface/session.py` (not frozen) was
  refactored behaviour-preservingly.
- **Two honest router-vs-engine divergences (pinned, neither a faithfulness breach):**
  `github_actions/05` — the offline synonymy miss the agent path inherits as a refusal
  (only embeddings bridge it; M11 is offline by choice); `business/05` — the bare term
  `"Logistik"` the production **router** answers with lexical matches where the eval's
  `compose` engine refuses as ambiguous. Pre-existing (the chat surface shares it);
  recorded as the **next lever** (align the router's ambiguity handling with `compose`).
- **The agent surface is read-only.** Grounded *actions* (effectful, or
  propose-and-approve, each grounded/cited/verifier-checked the same way) are the named
  next step — deferred by the maintainer's M11 scope, not a gap missed.
- ADR 0005 (LLM-judge) and ADR 0006 (semantic routing) triggers **re-examined at the
  boundary and recorded NOT forced** — no measured case forces either. The M6/M7 online
  HANA numbers remain timestamped, not CI-reproducible; M11 added no online number.

**Next milestone — to be defined with the maintainer.** Readiest candidates:
**grounded actions over MCP** (the natural M11 follow-through — propose-and-approve
tools, grounded and verifier-checked); **router-ambiguity alignment** (close the
business/05 agent-path gap, deterministic); a **second real connector** (Jira /
PR-and-issue export); full HANA graph persistence; BTP serving. The ER lever is spent;
ADR 0005/0006 triggers remain live and unacted.

**State of the tree**
- `main` green and in sync; no open branches. PRs #92–#96 merged. Tagged
  `milestone-11`.
