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

---

## 2026-06-30 — Milestone 12 COMPLETE (grounded actions over MCP)

**Mode note:** ran **autonomously** from one kickoff. The thrust and posture were the
three project-shaping decisions asked & answered 2026-06-29 and recorded in spec 0087
(grounded actions over MCP; deterministic/offline/no-spend; propose-and-approve only —
nothing executed). This session **resumed** an in-flight milestone: Units 1–2 (plan,
router alignment) were already merged and Unit 3 sat in open PR #100 awaiting its
mandated review. Six units total, each spec → branch → implement → gate → PR → CI-green
→ squash-merge. Fully **offline / CI-reproducible** (the M8–M11 posture); the MCP SDK
stays the opt-in `agent` extra.

**The problem this milestone answers.** Through eleven milestones the trust substrate —
grounded claims, claim-level provenance, a verifier gated at faithfulness 1.0 — only ever
produced **answers**. Milestone 11 made an agent *consume* them but stopped there (ADR
0022 recorded actions as the named next step). An agent that must *act* composed the
action itself, ungrounded, outside Tessera's guarantee. M12 extends the *same* substrate
to the **action draft**: a structured proposal whose every field traces to a
verifier-passing claim, or it is not proposed.

**Done this session (6 units, PRs #98–#103)**
- **Phase plan** (spec 0087, #98) + the three recorded scope decisions.
- **Router-ambiguity alignment** (spec 0088, #99): the business router defers a bare
  ambiguous term (`"Logistik"`, ties across two entities under `compose`'s resolver) to
  the refusing compose path, closing the M11 router-vs-engine divergence; the
  `business/05` pin removed from `tests/test_boundary.py`; no battery number moved.
- **The grounded-action layer** (spec 0089, ADR 0023, #100): `tessera/agent/actions.py`
  (additive, *not* frozen core) — `draft_action(kind, domain, question)` builds an
  `ActionProposal` strictly from a verifier-checked `GroundedResult`; each `ActionField`
  is a verbatim claim or evidence fragment with a **recomputed `verified`** verdict
  (source claim passed `is_supported` **and** the value is faithful), so `all_grounded`
  is earned (a provably-failable test). Declared catalog: `incident` (devex +
  github_actions RCA), `pr_summary` (devex change). Refused/incompatible/wrong-domain
  groundings carried with no fields. `requires_approval=True`/`executed=False`.
  **Carried its mandated pre-merge adversarial multi-agent review** (six lenses, 23
  agents, every finding independently reproduced): 16 confirmed findings, **2 fixed
  before merge** — (1) `_field` compared the value against a *concatenation* of all cited
  records (a seam-spanning token one weaker than the engine's per-record `is_supported`)
  → fixed to per-record containment, removed `_evidence_text`, behaviour-preserving; (2)
  a docstring/spec **overclaim** ("or it is not proposed at all" — the code surfaces an
  unverified field, doesn't withhold the proposal) → reworded. Plus regression pins
  (the seam, the full `_role` set, a github_actions refusal path, the partial-grounded
  state, the empty-fields `all_grounded` guard, determinism over all three shapes).
- **MCP action tools** (spec 0090, #101): thin `list_actions`/`draft_action` on
  `tessera-mcp` (no drafting logic; delegate verbatim to the layer); five tools now
  advertised; the no-`mcp`-in-base-graph pin holds; the committed `data/mcp_session/`
  client↔server session now also drafts an incident, a PR summary, and a **carried
  refusal**.
- **Trust across the action boundary** (spec 0091, #102): `tests/test_actions_boundary.py`,
  a CI-gated property over cases **derived from the data** (every failed run + every PR,
  14 today): each drafted action is field-grounded and a **lossless** projection of its
  grounding (value, support ids, *independently-recomputed* verdict per field), and
  **faithfulness is 1.0 across the action boundary**; a refusal is carried, never drafted.
  ADR 0005/0006 re-examined and recorded **still not forced**.
- **Close** (spec 0092, this entry, #103): the ADR 0008 **empty-diff frozen-core audit**
  (`milestone-11..HEAD` over the engine + verifier — **empty**); WRITEUP M12 section +
  updated limitations/future-work + a 10th "what was learned"; README (the action tools,
  the corrected scope: actions are *proposed* and field-verified, execution stays out);
  CHANGELOG `[milestone-12]`; ADR 0023 nav + index; tag `milestone-12`; memory; kickoff.

**Current eval numbers (unchanged — the action layer is a consumer, not a new path)**
- **business — gold 11: 1.000 / 1.000 / 1.000; synthetic 53: all 1.000.**
- **devex — gold 9: faithfulness 1.000, coverage 0.950 (offline) / 1.000 (online HANA,
  M7), quality 0.889 / 1.000; synthetic 24: all 1.000.**
- **github_actions — gold 5: faithfulness 1.000, coverage 0.833 / 1.000 (online, M7),
  quality 0.800 / 1.000; synthetic 8: all 1.000.**
- **New, recorded and gated in CI: faithfulness is 1.0 *across the action boundary*** over
  every data-derived action (`tests/test_actions_boundary.py`), the projection lossless.
  Deterministic across `PYTHONHASHSEED` 0/1/42/2026; **378 tests pass** with the `agent`
  extra (in CI 3 SDK contract tests skip → 375 pass, 378 collected).

**Milestone check (spec 0087 success criterion):** an enterprise AI agent can ask Tessera
over MCP to draft an action and receive a grounded, cited, verifier-checked **proposal**
(or a carried refusal) for the DevEx and real github_actions domains, offline and in CI;
every drafted field is field-grounded and the projection lossless (measured); a refusal
never becomes a drafted action; the default clone-and-run + CI stay pure-stdlib; the
router divergence is closed and no battery number moved; **zero frozen-core delta**.
**Met.** Tagged `milestone-12`.

**Open questions / risks**
- **Frozen core untouched** (ADR 0008): the empty-diff audit `milestone-11..HEAD` over the
  engine + verifier is **empty**. The only existing-code production change is the
  vertical-side `business/routing.py` (Unit 2, reviewed); everything else is the additive
  `tessera/agent/` package, tests, specs, and the ADR.
- **The honest edge: propose-and-approve, nothing executed.** Tessera guarantees the
  *draft* is grounded; it executes nothing, calls no external system, renders no payload.
  Effectful execution (and a dry-run payload preview) is the named next step, deliberately
  out of scope (credentialed/irreversible — outside the honest scope of a trust layer,
  ADR 0023).
- **The structural-verifier limit (ADR 0005) carries through:** a field `verified=True`
  means it is mechanically supported by its citation, not that the action is wise. The
  approver still judges. ADR 0005 (LLM-judge) and 0006 (semantic routing) re-examined at
  the action boundary and recorded **not forced**; no measured case forces either. The
  M6/M7 online HANA numbers remain timestamped, not CI-reproducible; M12 added no online
  number.

**Next milestone — to be defined with the maintainer.** Readiest candidates:
**effectful execution behind approval** (the named M12 follow-through — a credentialed,
reversible-where-possible actuator with the proposal as the gated precondition; the first
time Tessera would *do* something, so the biggest posture decision) / a **dry-run
executable-payload preview** (a smaller step toward execution — render the exact external
API payload without sending it) / a **second real connector** (Jira / PR-and-issue export,
a third drop-in proof) / **full HANA graph persistence** / **BTP serving** (container → AI
Core / Kyma). The ER lever is spent (registry-only residual); ADR 0005/0006 triggers
remain live and unacted.

**State of the tree**
- `main` green and in sync; no open branches. PRs #98–#103 merged. Tagged
  `milestone-12`.

---

## 2026-06-30 — Milestone 13 COMPLETE (the dry-run executable-payload preview)

**Mode note:** ran **autonomously** from one kickoff after a project-shaping scope
discussion. The maintainer chose (asked 2026-06-30): **(1) thrust** — the dry-run
executable-payload preview (over effectful execution / a second connector / HANA
persistence / BTP serving); **(2) target** — GitHub (incident → create-issue,
pr_summary → PR comment); **(3) posture** — deterministic / offline / CI-reproducible /
no-spend (the M8–M12 posture). Five units, each spec → branch → implement → gate → PR →
CI-green → squash-merge. Fully **offline / CI-reproducible** — the MCP SDK stays the
opt-in `agent` extra.

**The problem this milestone answers.** Through twelve milestones the trust substrate
produced grounded **answers** (M11) and grounded **action drafts** (M12) — but stopped
short of the wire: M12's `ActionProposal` records the edge in its own docstring, it
"renders no executable payload." An agent that had to *act* still composed the wire
request itself, ungrounded. ADR 0023 named the two deferred scopes — effectful execution
and a dry-run payload preview — and declined both for M12. M13 takes the smaller,
in-character one: render the **exact GitHub request** a grounded action would send, every
value traced to a verifier-passing field, and **send nothing**. The same measured
boundary pattern a third time (read → action draft → executable payload).

**Done this session (5 units, PRs #104–#107 + this close)**
- **Phase plan** (spec 0093, #104) + the three recorded scope decisions + the finer
  decisions (both catalog kinds rendered; rendered iff `all_grounded`; grounded values
  vs. declared scaffolding named honestly) + the design for ADR 0024.
- **The GitHub payload renderer + ADR 0024** (spec 0094, #105): `tessera/agent/payloads.py`
  (additive, *not* frozen core) — `render_payload(proposal)` / `preview_payload(action,
  domain, question)` turn a verifier-checked `ActionProposal` into a `RenderedPayload`
  (method, path, JSON body, traceable slots). Every content value is one verified field
  (issue title, body sections, the `{pr}` resource id); everything else is declared
  scaffolding (section labels, fences, fixed issue `labels`, unbound `{owner}`/`{repo}`),
  never asserted grounded. Rendered iff `all_grounded` (refused / partial /
  route-incompatible / wrong-domain / undeclared-role / no-title → **withheld**, no
  request); `sent=False` / `requires_approval=True`. The wire request is
  byte-reconstructable from the verified fields. Leak-guard extended.
  **Carried its mandated pre-merge adversarial multi-agent review** (6 lenses, 12 agents,
  every finding independently reproduced): **0 majors, 4 minors + 2 nits, all fixed
  before merge** — (1) the `{pr}` segment took `support[0]` with no PR-record guard
  (`removeprefix('PR:')` a silent no-op for a non-PR id) → select the first `PR:`-prefixed
  record, require a clean single segment, else withhold; (2) the `pr_summary` subject was
  read positionally (`fields[0]` is the lifted title, correct only by accident) → select
  by role; (3) the subtractive anti-smuggle residue check had blind spots (path uncovered,
  blanket fence-strip, first-occurrence removal, unmapped-label asymmetry) → replaced with
  **independent positive reconstruction equality** over method+path+body+labels; (4) the
  fixed `labels` overclaimed "every value traces to a verified field" → reworded
  docstring/ADR/spec to "...or is declared scaffolding," vocabulary closed (an undeclared
  field role is withheld, not given an invented heading). Each pinned by a regression test.
- **MCP `preview_payload` tool** (spec 0095, #106): a thin sixth tool on `tessera-mcp`
  delegating verbatim to the renderer (a test pins handler output == the layer's
  `to_dict()`); the no-`mcp`-in-base pin holds; the committed `data/mcp_session/` session
  now also previews a rendered create-issue, a rendered PR comment (path bound to the
  traced `PR-201`), and a withheld payload — `sent=false` throughout.
- **Trust across the payload boundary** (spec 0096, #107): `tests/test_payloads_boundary.py`,
  a CI-gated property over data-derived cases (every failed run + every PR, 14 today): each
  rendered payload is field-grounded + a **lossless** projection of its grounding (value,
  support ids, *independently-recomputed* verdict per slot) + byte-reconstructable; and
  **faithfulness is 1.0 across the payload boundary**; a withheld payload carries no
  request. ADR 0005/0006 re-examined and recorded **still not forced**.
- **Close** (spec 0097, this entry): the ADR 0008 **empty-diff frozen-core audit**
  (`milestone-12..HEAD` over the engine + verifier **and** the vertical answer layers —
  **empty**); WRITEUP M13 section + updated limitations/future-work + an 11th "what was
  learned"; README (the preview tool, the corrected scope: payloads are *rendered* not
  *sent*); CHANGELOG `[milestone-13]`; ADR 0024 nav + index (added in Unit 2); tag
  `milestone-13`; memory; kickoff.

**Current eval numbers (unchanged — the payload layer is a consumer, not a new path)**
- **business — gold 11: 1.000 / 1.000 / 1.000; synthetic 53: all 1.000.**
- **devex — gold 9: faithfulness 1.000, coverage 0.950 (offline) / 1.000 (online HANA,
  M7), quality 0.889 / 1.000; synthetic 24: all 1.000.**
- **github_actions — gold 5: faithfulness 1.000, coverage 0.833 / 1.000 (online, M7),
  quality 0.800 / 1.000; synthetic 8: all 1.000.**
- **New, recorded and gated in CI: faithfulness is 1.0 *across the payload boundary*** over
  every data-derived payload (`tests/test_payloads_boundary.py`), the projection lossless
  and the wire request byte-reconstructable. Deterministic across `PYTHONHASHSEED`
  0/1/42/2026; **404 tests pass** with the `agent` extra (in CI the SDK contract tests
  skip).

**Milestone check (spec 0093 success criterion):** an enterprise AI agent can ask Tessera
over MCP to preview the exact GitHub request a grounded action would send and receive a
byte-exact payload whose every value is field-grounded (or a carried withheld result),
offline and in CI; every payload value traces to a verifier-passing field and the request
is byte-reconstructable (measured); a payload is never rendered over ungrounded ground;
nothing is sent; the default clone-and-run + CI stay pure-stdlib; **zero frozen-core
delta**. **Met.** Tagged `milestone-13`.

**Open questions / risks**
- **Frozen core untouched** (ADR 0008): the empty-diff audit `milestone-12..HEAD` over the
  engine + verifier **and** the business/devex answer layers is **empty**. The whole
  milestone is the additive `tessera/agent/payloads.py` + the thin MCP tool + tests +
  specs + the ADR + docs.
- **The honest edge: render ≠ send, nothing executed.** Tessera guarantees the *request*
  is grounded; it renders it but sends nothing, opens no socket, holds no credential
  (`{owner}`/`{repo}` stay unbound). Effectful execution behind approval is the named next
  step, deliberately out of scope (credentialed/irreversible; done honestly it would
  *consume* this renderer — a simulated default actuator + opt-in real path + receipt).
- **Synthetic-data note:** real GitHub PR comments address the numeric PR number; the
  synthetic DevEx ids are `PR-NNN`, used verbatim as the grounded resource id in the
  dry-run path. The shape and grounding are real; the resource id reflects our data.
- **The structural-verifier limit (ADR 0005) carries through:** a slot `verified=True`
  means its value is mechanically supported by its citation, not that sending the request
  is wise. ADR 0005 (LLM-judge) and 0006 (semantic routing) re-examined at the payload
  boundary and recorded **not forced**; no measured case forces either. The M6/M7 online
  HANA numbers remain timestamped, not CI-reproducible; M13 added no online number.

**Next milestone — to be defined with the maintainer.** Readiest candidates: **effectful
execution behind approval** (the named M13 follow-through — the first time Tessera would
*do* something; the biggest posture decision; done honestly it consumes this renderer with
a simulated default + opt-in real actuator + execution receipt) / a **second payload
target** (Jira create-issue, proving the field-grounding contract generalizes across target
schemas) / a **second real connector** (Jira / PR-and-issue export) / **full HANA graph
persistence** / **BTP serving** (container → AI Core / Kyma). The ER lever is spent
(registry-only residual); ADR 0005/0006 triggers remain live and unacted.

**State of the tree**
- `main` green and in sync; no open branches. PRs #104–#107 merged. Tagged
  `milestone-13`.

---

## 2026-07-01 — Milestone 14 COMPLETE (effectful execution behind approval, simulated by default)

**Mode note:** ran **autonomously** from one kickoff after a project-shaping scope
discussion. The maintainer chose (asked 2026-07-01): **(1) thrust** — effectful
execution behind approval (over a second payload target / a second connector / HANA
persistence / BTP serving); **(2) posture** — a **simulated core + an opt-in real seam
that sends nothing in-repo** (over *also* doing a maintainer-authorized real one-shot,
and over a simulated-only build with no real adapter). Five units, each spec → branch →
implement → gate → PR → CI-green → squash-merge. Fully **offline / CI-reproducible**.

**The problem this milestone answers.** Through thirteen milestones Tessera only ever
*rendered* the wire request and sent nothing (M13: `sent=False`, `{owner}`/`{repo}`
unbound). An agent that had to *act* took that request and sent it itself, outside
Tessera's guarantee. ADR 0023/0024 named effectful execution as the next step and
recorded how to do it honestly in a clone-and-run/CI project: a simulated default
actuator + an opt-in real path + an execution receipt — it would *consume* the M13
renderer. M14 takes it, reaching the fourth measured boundary: read (M11) → action draft
(M12) → executable payload (M13) → **execute** (M14).

**Done this session (5 units, PRs #109–#112 + this close)**
- **Phase plan** (spec 0098, #109) + the two recorded scope decisions + the finer
  decisions + the design for ADR 0025.
- **The actuator + `ExecutionReceipt` + ADR 0025** (spec 0099, #110):
  `tessera/agent/execution.py` (additive, *not* frozen core) — an `Actuator` protocol;
  `SimulatedActuator` (the default — records the exact would-be request, sends nothing,
  transparently synthetic, no fabricated resource id); an opt-in `GithubActuator` (stdlib
  `urllib`, an injected `Transport`, approval + credential gated, its real
  transport/network never invoked in CI, contract-tested vs a fake transport);
  `ExecutionReceipt` (lossless, JSON-serializable); and `execute_action` /
  `execute_payload` **gated on `RenderedPayload.all_grounded`** — nothing executes over
  ungrounded ground. The real path is double-gated (approval **and** credential), so
  `sent=True` is *earned*. Leak-guard extended (executing pulls no
  embedding/LLM/`hdbcli`/`mcp` import; the simulated path opens no socket).
  **Carried its mandated pre-merge adversarial multi-agent review** (6 lenses, 9 agents,
  every finding independently reproduced): **0 majors**, 3 confirmed findings, all fixed
  before merge — (1) the receipt aliased the payload's mutable `body` dict → copy on
  inherit; (2) `blocked`/`error` receipts set `withheld_reason` while `withheld=False` →
  reserved `withheld_reason` for the ungrounded gate, carry block/error detail in
  `outcome`+`result`; (3) "never invoked in CI" **overclaimed** the actuator (it *is*
  contract-tested in CI against a fake transport — only the real transport/network is
  not) → scoped across the docstrings, ADR 0025, and the specs. Each pinned by a
  regression test.
- **MCP `execute_action` tool** (spec 0100, #111): a thin seventh tool on `tessera-mcp`
  wired to the **simulated** actuator only (the server holds no credential and can never
  send); the no-`mcp`-in-base pin holds; a contract test pins handler output == the
  layer's `to_dict()`; the committed `data/mcp_session/` session now also runs a
  simulated create-issue execution, a simulated PR-comment execution, and a withheld
  execution (`sent=false` throughout).
- **Trust across the execution boundary** (spec 0101, #112):
  `tests/test_execution_boundary.py`, a CI-gated property over data-derived cases (every
  failed run + every PR): every simulated execution consumed an `all_grounded` payload
  and its receipt is a **lossless** record (each slot's verdict recomputed independently
  from the grounding); **faithfulness is 1.0 across the execution boundary**; nothing
  executes over ungrounded ground; the real path sends iff approved+credentialed (fake
  transport). ADR 0005/0006 re-examined and recorded **still not forced**.
- **Close** (spec 0102, this entry): the ADR 0008 **empty-diff frozen-core audit**
  (`milestone-13..HEAD` over the engine + verifier + the vertical answer layers + the
  M11/M13 agent layers — **empty**; only `agent/execution.py` new + `agent/mcp_server.py`
  thin tool); WRITEUP M14 section + updated limitations/future-work + a 12th "what was
  learned"; README (the execute tool, the four measured boundaries, the corrected scope:
  simulated by default, real path opt-in behind credentials+approval, nothing sent from
  this repo); CHANGELOG `[milestone-14]`; ADR 0025 nav + index (added in Unit 2); tag
  `milestone-14`; memory; kickoff.

**Current eval numbers (unchanged — the execution layer is a consumer, not a new path)**
- **business — gold 11: 1.000 / 1.000 / 1.000; synthetic 53: all 1.000.**
- **devex — gold 9: faithfulness 1.000, coverage 0.950 (offline) / 1.000 (online HANA,
  M7), quality 0.889 / 1.000; synthetic 24: all 1.000.**
- **github_actions — gold 5: faithfulness 1.000, coverage 0.833 / 1.000 (online, M7),
  quality 0.800 / 1.000; synthetic 8: all 1.000.**
- **New, recorded and gated in CI: faithfulness is 1.0 *across the execution boundary***
  over every data-derived execution (`tests/test_execution_boundary.py`), the receipt a
  lossless record and nothing executed over ungrounded ground. Deterministic across
  `PYTHONHASHSEED` 0/1/42/2026; **430 tests pass** with the `agent` extra (in CI the SDK
  contract tests skip).

**Milestone check (spec 0098 success criterion):** an enterprise AI agent can ask
Tessera over MCP to execute a grounded action and receive an `ExecutionReceipt` for a
**simulated** execution — the exact request that would be sent, every value
field-grounded, and nothing sent — or a carried **withheld** receipt when the action is
not fully grounded, offline and in CI; every simulated execution consumed an
`all_grounded` payload and its receipt is a lossless record (measured); nothing executes
over ungrounded ground; the real path sends iff approved+credentialed (fake transport);
the default clone-and-run + CI stay pure-stdlib; **zero frozen-core delta**. **Met.**
Tagged `milestone-14`.

**Open questions / risks**
- **Frozen core untouched** (ADR 0008): the empty-diff audit `milestone-13..HEAD` over
  the engine + verifier + the business/devex answer layers + the M11/M13 agent layers is
  **empty**. The whole milestone is the additive `tessera/agent/execution.py` + the thin
  MCP tool + tests + specs + the ADR + docs.
- **The honest edge: render/simulate ≠ send; nothing leaves this repository.** The
  default `SimulatedActuator` (used by tests, CI, clone-and-run, and the MCP surface)
  sends nothing. The real `GithubActuator` is built and contract-tested against a *fake*
  transport, but its real transport/network is never invoked in CI and it is never
  constructed by the default path. Actually sending — a maintainer-authorized real
  one-shot — is the named next posture step, deliberately not taken (credentialed and
  irreversible). A real create-issue is not idempotent; recorded as a caller
  responsibility (the receipt is auditable before approval), not engineered.
- **The structural-verifier limit (ADR 0005) carries through:** a receipt slot
  `verified=True` means its value is mechanically supported by its citation, not that
  performing the action is wise; approval is the second gate on the real path, and the
  approver still judges. ADR 0005 (LLM-judge) and 0006 (semantic routing) re-examined at
  the execution boundary and recorded **not forced**; no measured case forces either. The
  M6/M7 online HANA numbers remain timestamped, not CI-reproducible; M14 added no online
  number.

**Next milestone — to be defined with the maintainer.** Readiest candidates: **actually
sending behind approval** (a maintainer-authorized real GitHub one-shot — the first real
side effect, credentialed/spend-adjacent/irreversible; the seam is built and
contract-tested, so it is a small, separate posture decision) and/or **engineered
idempotency** on the real path / a **second payload+execution target** (Jira create-issue,
proving the actuator contract generalizes across target schemas) / a **second real
connector** (Jira / PR-and-issue export) / **full HANA graph persistence** / **BTP
serving** (container → AI Core / Kyma). The ER lever is spent (registry-only residual);
ADR 0005/0006 triggers remain live and unacted.

**State of the tree**
- `main` green and in sync; no open branches. PRs #109–#112 merged. Tagged
  `milestone-14`.

---

## 2026-07-01 — Milestone 15 Units 2–3 + recorder refactor *(backfilled)*

**Honesty note:** this entry was **reconstructed on 2026-07-02** (Milestone 16
Unit 1, spec 0108) from PRs #115–#117 and ADR 0026. The sessions that merged
them ended without `/wrap`, and their spec numbers (0104–0106) were consumed in
commit messages without spec files — the audit's findings D1/D3; see the
`specs/README.md` numbering ledger. Recorded so the journal stays resumable;
the numbers below were re-verified live on 2026-07-02.

**Done (PRs #115–#117, following the 0103 plan merged as #114)**
- **Best-effort idempotency on the real execution path + ADR 0026** ("0104",
  PR #115): `idempotency_key` (sha256 over the canonical grounded
  method/path/body), a three-surface marker (HTML comment + visible footer +
  `idem-<hex16>` label), `Transport.get`, a paging pre-send existence check on
  the primary issues/comments endpoint, and the new `exists`/`inconclusive`
  outcomes — refuse, never silently duplicate. The implemented pre-check
  deliberately dropped the 0103-planned search-API leg (eventual consistency)
  for primary-endpoint paging; ADR 0026 records the implemented design.
  Adversarial review ran (pagination finding fixed).
- **Recorder + scrubber + runbook** ("0105", PR #116):
  `scripts/record_real_execution.py` (maintainer-only, never CI),
  `tessera.agent.recording.redact_receipt` (response allow-list
  `number`/`html_url`/`state`/`title` + token-like-key redaction), the
  DEPLOYMENT one-shot runbook, `.env.example`, `data/execution/` layout, and a
  regenerated `data/mcp_session/` for the receipt-field ripple.
- **Recorder records only an approved send** ("0106", PR #117): a rehearsal
  (no `TESSERA_EXEC_APPROVE=true`) writes nothing, so it can never be mistaken
  for, or committed as, the one-shot.

**Current eval numbers** — unchanged (the idempotency work is real-path-only;
no battery number moved; faithfulness floors 1.0).

**Next**
- M15 Units 4–5 — the maintainer-triggered real send + the milestone close —
  **gated behind Milestone 16 Unit 2** (audit findings B1–B4 touch the
  one-shot's artifact and safety and must land first).

**State of the tree**
- `main` green and in sync; no open branches. PRs #114–#117 merged. Not tagged
  (M15 stays in flight until its Units 4–5 close).

---

## 2026-07-02 — Act 2 kickoff: audit, market research, and the productization roadmap

**Mode note:** a maintainer-directed **re-orientation session** after ~10
autonomous milestones — no feature code. The maintainer asked for: an honest
state-of-the-project audit ("does it work, is it reliable, what drifted?"), and
a researched plan pointing the next month at two goals at once — the SAP
internship and the Z Fellows cohort (customer-ready MVP + visible traction).

**Done this session**
- **Full drift audit + trust-path bug hunt + clean-room run verification** →
  [`docs/AUDIT_2026-07-02.md`](AUDIT_2026-07-02.md). Headline: everything runs
  exactly as documented (gate green, 443/443 tests, live eval numbers match
  badge/history/README digit-for-digit; all seven demo doors + MCP boot
  verified). Drift is real but shallow: STATUS/CHANGELOG lag the four merged
  M15 PRs, seven phantom spec numbers (incl. 0104–0106), WRITEUP/DEPLOYMENT
  staleness, and **eight code findings (B1–B8)** — none in the core engine; the
  serious ones sit in the new M15 real-execution path (receipt clobbering,
  label-dependent idempotency, PAT in `repr`, markdown-fence injection).
- **Market/program research** (agent-assisted, three strategy-critical claims
  independently re-verified) → [`docs/MARKET.md`](MARKET.md). The gap is
  confirmed: nobody credibly combines per-claim provenance + evidence-gated
  actions with receipts + a self-shipped deterministic faithfulness benchmark +
  on-prem determinism (closest: Palantir AIP, the AWS Bedrock stack, Quantexa).
  SAP standardized on MCP and wired Claude in via MCP (Sapphire, May 2026);
  SAP's trust story is asserted (Agent Hub "verification badges"), not
  measured — Tessera's exact wedge. Z Fellows verified as a one-week,
  mostly-virtual cohort (no investor demo day; in-cohort presentation;
  the $100k follow-on + network are the prize). EU AI Act Annex-III
  obligations deferred to Dec 2027 (Digital Omnibus) — deadline-panic
  positioning is stale; "audit-ready by design" stays a tailwind.
- **The Act 2 roadmap** → [`docs/ROADMAP2.md`](ROADMAP2.md): M16 close & clean
  (audit fixes + finish M15 with the maintainer one-shot) → M17 demoable to
  humans (narration, web UI over the existing trust objects, hosted demo,
  "agent through Tessera" demo) → M18 usable on your data (BYO GitHub repo +
  CSV/docs dir — the design-partner pilot vehicle) → M19 launch & traction
  (registries, the "Faithfulness Floor" benchmark, Show HN, 100–150 DACH
  outreach, Z Fellows kit) + a parallel SAP track (SALT real-data eval, HANA
  KG persistence, BTP serving, application kit). Positioning fixed: *"The
  agent can only say what it can prove — and only do what you approve."*

**Current eval numbers (re-verified live this session, unchanged)**
- **business — gold 11: 1.000 / 1.000 / 1.000; synthetic 53: all 1.000.**
- **devex — gold 9: 1.000 / 0.950 / 0.889 (offline); synthetic 24: all 1.000.**
- **github_actions — gold 5: 1.000 / 0.833 / 0.800 (offline); synthetic 8: all 1.000.**

**Next**
- **M16 Unit 1** (drift repair) via `/spec`, then Units 2–3 (audit fixes B1–B7),
  then the **maintainer decisions** blocking M15's close and Act 2's cadence —
  see the checklist in [`ROADMAP2.md`](ROADMAP2.md): the real one-shot
  (PAT + sandbox repo), HANA instance health check, SALT access request,
  Anthropic key, hosting, BTP account, Z Fellows cohort dates, launch consent.

**Open questions / risks**
- The eight maintainer decisions above are the only blockers; everything else
  proceeds autonomously per CLAUDE.md.
- Audit B1–B4 must land **before** the M15 real one-shot (they affect the
  one-shot's artifact and safety).
- MARKET.md is a dated snapshot (2026-07-02); re-verify load-bearing claims
  before quoting externally.

**State of the tree**
- `main` green and in sync. This session adds three docs
  (`AUDIT_2026-07-02.md`, `MARKET.md`, `ROADMAP2.md`), this entry, and their
  mkdocs nav wiring — via branch → PR per branch protection. No code changes.
  Not tagged (M15 remains in flight until its Units 4–5 close).

---

## 2026-07-02 — Milestone 16 Units 1–4 COMPLETE (close & clean; the one-shot is two commands away)

**Mode note:** maintainer-directed start the same day as the audit ("begin M16
and prepare the one-shot so I can execute it without problems"). Context
corrections recorded: the maintainer is a Z Fellows **applicant in final
selection** (a one-month build period with weekly ship-updates and a check-in
presentation — ROADMAP2 updated), and the Anthropic API key is now in `.env`
(ROADMAP2 decision #4, done). Units per discipline: spec → branch → gate → PR
→ CI-green → squash-merge (PRs #119–#123).

**Done this session**
- **Plan** (spec 0107, #119): unit breakdown + six recorded decisions
  (forward-only spec numbering; recorder persistence policy; label-independent
  pre-check; transparent-verifier rule; public sandbox repo; M16 tags at its
  close, which includes M15's).
- **Unit 1 — drift repair** (spec 0108, #120): audit D1–D7 acted on — STATUS
  backfill for the M15 sessions (honestly labeled), CHANGELOG, WRITEUP
  idempotency truth, DEPLOYMENT embeddings row ("built and measured on SAP"),
  README count/pointers/M15-in-flight wording, CAPABILITIES future-work
  markers, the `specs/README.md` numbering ledger, ROADMAP2 Z-Fellows
  correction — plus **68 stale merged remote branches pruned** (3 refs remain:
  main + two dependabot).
- **Unit 2 — trust-path fixes B1–B5** (spec 0109, #121): recorder
  never-clobbers (policy in tested `recording.py`; case-insensitive guard,
  exclusive-create, persist only `created`/`exists`, non-consummated approved
  attempts print + exit non-zero); the idempotency pre-check is
  **label-independent** (unfiltered `state=all` marker scan; ADR 0026
  addendum); `token` excluded from `repr`; **content-proof fences** (per-value
  length; ADR 0024 addendum); `{pr}` allowlist. **Carried the mandated 5-lens
  pre-merge adversarial review** (recorder correctness, GitHub semantics —
  docs-verified, security, faithfulness contract, docs honesty; every finding
  independently reproduced): **3 confirmed majors, all fixed before merge** —
  (1) the CI-gated boundary reconstruction still hardcoded the old fence
  (rule ported); (2) the recorder's MANIFEST note promised the pre-B1 re-run
  behavior (reworded); (3) the ADR 0026 addendum misstated the original ADR's
  history (reworded; audit table corrected; superseded-markers added). Review
  hardening also landed: the real transport **refuses redirects** (urllib
  forwards `Authorization` cross-origin and rewrites POST→GET — a moved repo
  could have minted a false `created`); multiline values in non-fenced roles
  withhold the payload; the spoofed-`exists`-is-persistable residual is named
  (verify-the-URL step in the runbook); null-body/PR items in the pre-check
  test fake.
- **Unit 3 — verifier honesty** (spec 0110, #122): refuse-kind claims are now
  faithfulness-scored (audit B7; measured effect zero — all six battery lines
  byte-identical, the floor's reach widened); over-citation and
  cross-word-boundary containment named in an ADR 0005 addendum and pinned by
  committed specimens (audit B6).
- **Unit 4 — one-shot preparation** (spec 0111, #123): public sandbox repo
  **created** (`robert-vetter/tessera-exec-oneshot`, with purpose README);
  `.env` prefilled with the non-secret `TESSERA_EXEC_*` values (PAT
  placeholder + mint link); DEPLOYMENT runbook rewritten for the post-0109
  recorder (incl. the verify-the-issue-URL honesty step and the
  labels-silently-dropped note); the **M15 close checklist** recorded in the
  spec so any session can execute it after the send. The no-credential
  instructions path re-verified live (prints instructions, sends nothing).

**Current eval numbers (unchanged throughout — verified at every unit's gate)**
- **business — gold 11: 1.000 / 1.000 / 1.000; synthetic 53: all 1.000.**
- **devex — gold 9: 1.000 / 0.950 / 0.889 (offline); synthetic 24: all 1.000.**
- **github_actions — gold 5: 1.000 / 0.833 / 0.800 (offline); synthetic 8: all 1.000.**
- **461 tests** (443 → +18 across 0109/0110); gate green on every PR.

**Next**
- **The maintainer's one-shot** (spec 0111): mint the fine-grained PAT
  (Issues RW on `tessera-exec-oneshot` only), paste it into `.env`, run the
  rehearsal, run the approved send, verify the printed issue URL.
- Then any session executes the **0111 close checklist** → commit the scrubbed
  receipt → WRITEUP/README/CHANGELOG → empty-diff audit → tags `milestone-15`
  + `milestone-16` → hand back the **M17 kickoff** (demoable to humans:
  narration, web UI over the existing trust objects, hosted demo — the
  Z Fellows "live demo anyone can try" commitment).

**Open questions / risks**
- The remaining maintainer decisions (ROADMAP2 checklist): HANA instance
  health, SALT HF access request, hosting choice, BTP account, the Z Fellows
  check-in date, launch consent. None blocks the one-shot.
- Two open dependabot PRs (#59 actions/cache, #60 python group) — take through
  a normal gate cycle when convenient.
- The sandbox repo is public and idle until the send — run the one-shot soon
  (the runbook's verify-URL step covers the remote spoof case regardless).

**State of the tree**
- `main` green and in sync; no open unit branches. PRs #118–#123 merged this
  day. Not tagged (M15/M16 tag together after the send, per spec 0107
  decision 6).

---

## 2026-07-03 — Milestones 15 + 16 COMPLETE (Tessera actually sent — once, on the record)

**Mode note:** the maintainer executed the one-shot himself (spec 0103
decision 3: the credential never enters the agent's environment; the agent
prepared, verified, and closed). This entry is the close per the spec 0111
checklist.

**THE RECORDED REAL SEND (2026-07-03, ~12:00 CET)**
- **[`tessera-exec-oneshot#1`](https://github.com/robert-vetter/tessera-exec-oneshot/issues/1)**
  — a grounded incident for the **real** CI failure of run 27014662820 (the
  Phase-1 format-check break), `outcome="created"`, `sent=true`, status 201,
  idempotency key `sha256:08dc3d0c…`, marker + `incident`/`idem-` labels
  attached. Verified post-send: author `robert-vetter`, exact marker present in
  the issue body.
- The scrubbed `ExecutionReceipt` + `MANIFEST` are **committed** at
  `data/execution/` — credential absent by construction, GitHub's echo reduced
  to `number`/`html_url`/`state`/`title`, gitleaks green.
- **The failure path proved itself in the wild first:** the maintainer's first
  attempt ran against a wrong (read-only) token in `.env` — GitHub answered
  403, and the freshly-hardened recorder printed the full scrubbed receipt,
  **persisted nothing**, exited non-zero, and left the retry unblocked (the
  0109/B1 policy, on its first real use). A second `.env` mishap (a manual
  paste overwrote the file, including the HANA and Anthropic entries) was
  repaired without the token ever entering the session; the lost `HANA_*` /
  `ANTHROPIC_API_KEY` values must be re-added by the maintainer.
- Diagnosis trail for the 403 (all side-effect-free): token valid & owned by
  the maintainer, public reads 200, PATCH-nonexistent 404, label-create probe
  403 "Resource not accessible by personal access token" → the `.env` held an
  older read-only PAT; the freshly-minted Issues-RW token fixed it.

**Milestone 15 check (spec 0103/0111):** engineered best-effort idempotency,
contract-tested offline (Unit 2, ADR 0026 + addendum) ✓; recorder + scrubber +
runbook (Unit 3) ✓; **one recorded real send** with committed scrubbed receipt
(Unit 4) ✓; close: WRITEUP M15–16 section + limitations flip, README
(twelve milestones; "sent exactly once, on the record"), CHANGELOG
`[milestone-15]` + `[milestone-16]`, `data/execution/README` updated, the ADR
0008 **empty-diff frozen-core audit over `milestone-14..HEAD` CLEAN** (only
sanctioned deltas: `agent/execution.py`, `agent/payloads.py`,
`agent/recording.py` — ADR 0026/0024 + spec 0109 — and `eval/harness.py` —
ADR 0005 addendum / spec 0110) ✓. **Met. Tagged `milestone-15`.**

**Milestone 16 check (spec 0107):** audit findings fixed or ADR-accepted
(D1–D7 in 0108; B1–B5 in 0109 with the 5-lens review; B6–B7 in 0110; B8
noted) ✓; `milestone-15` tagged ✓; STATUS current ✓; gate green throughout ✓.
**Met. Tagged `milestone-16`.**

**Current eval numbers (unchanged; verified at the close gate)**
- **business — gold 11: 1.000 / 1.000 / 1.000; synthetic 53: all 1.000.**
- **devex — gold 9: 1.000 / 0.950 / 0.889 (offline); synthetic 24: all 1.000.**
- **github_actions — gold 5: 1.000 / 0.833 / 0.800 (offline); synthetic 8: all 1.000.**
- 461 tests; the real send is a timestamped recorded measurement (the M6/M7
  "ran on X" pattern), not a CI gate; CI stays offline and key-free.

**Next — Milestone 17 (ROADMAP2): demoable to humans.** Narration on the demo
surface (ADR 0013; the Anthropic key needs re-adding to `.env` first), the web
UI over the existing trust objects (`ui` extra; stack choice is an ADR), the
hosted read-only demo + 2–3-minute video, and the "agent through Tessera over
MCP" scripted demo — the Z Fellows commitment ("a live demo anyone can try"),
scheduled. Kickoff prompt handed back in the session summary.

**Open questions / risks**
- Maintainer to re-add `HANA_*` + `ANTHROPIC_API_KEY` to `.env` (overwritten
  2026-07-03; placeholders + notes are in the file).
- Remaining ROADMAP2 decisions: HANA instance health, SALT HF access request,
  hosting choice, BTP account, the Z Fellows check-in date, launch consent.
- Dependabot #59/#60 still open.
- The sandbox issue is public and open — leave it open (it *is* the record);
  closing it later does not invalidate the receipt.

**State of the tree**
- `main` green and in sync; no open unit branches. PRs #118–#125 merged.
  **Tagged `milestone-15` + `milestone-16`.**

---

## 2026-07-03 — Milestone 17 Units 2–5 COMPLETE (demoable to humans; tag pends the maintainer's deploy)

**Mode note:** ran autonomously from the maintainer's "starte M17" (Anthropic
key + HANA re-added to `.env`). Presentation layer only — a strict consumer of
the existing trust objects; no engine/verifier/boundary change. Units per
discipline: spec → branch → gate → PR → CI-green → squash-merge (PRs #126–#131).

**Done this session**
- **Plan** (spec 0112, #126): six recorded decisions — stdlib UI (ADR 0027 at
  Unit 3), no credential in the UI by construction, evidence text stays
  verbatim (presentation via narration/UI, never munging), the agent demo over
  the real MCP server, asset split (agent builds; maintainer deploys/records),
  cosmetics in passing.
- **Unit 2 — narration live + cosmetics** (spec 0113, #127): the ADR 0013
  narration boundary **exercised live for the first time** (Anthropic, default
  Haiku) — narration rendered under its label below the canonical claims,
  trust line 8/8; refusals stay un-narrated. `:trust` float precision + MCP
  `serverInfo` project version, both test-pinned.
- **Unit 3 — the web surface** (spec 0114, ADR 0027, #128): `uv run tessera-ui`
  — one page, pure stdlib, zero JS, strict CSP, escape-everything: ask → routed
  answer with per-claim verifier chips → provenance drill-down (records,
  locators, ER trail) → refusal cards → action draft → dry-run payload →
  explicit approve → **simulated** receipt. Holds no credential; no code path
  to the real actuator. Verified visually via local preview. **Three focused
  adversarial reviews (security ×2 + trust-honesty): 0 majors** — surface
  holds (escaping complete, CSP truthful, no egress); all confirmed minors
  fixed (POST-body cap, URL-encoded query values, CSP hardening, offer/preview
  gating on `all_verified`/`all_grounded`, cached history read, count-accurate
  copy), each pinned. 16 UI tests.
- **Unit 4 — a real Claude agent grounded only through the MCP tools**
  (spec 0115, #129): `scripts/record_agent_session.py` ran a real Sonnet-5
  agent over the real `tessera-mcp` stdio server with **only** Tessera's seven
  tools. Recorded to `data/agent_session/`: turn 1 grounded RCA with cited
  evidence; turn 2 R-1041 *passed* → the agent reports the refusal, no
  fabrication; turn 3 draft → preview → **simulated** receipt (`sent: false`).
  The headline demo of the thesis, on the record.
- **Unit 5 — hosted packaging + assets** (spec 0116, #130 + docfix #131):
  `docs/DEMO.md` — the key-free hosting runbook (Fly.io / Railway / VM+Caddy;
  verified the UI binds `0.0.0.0`), the 3-minute demo script (the post-Replit
  arc as four clickable beats), and the EN+DE one-pager. README leads the demo
  section with `tessera-ui`.

**Current eval numbers (unchanged — the whole milestone is a consumer)**
- **business — gold 11: 1.000 / 1.000 / 1.000; synthetic 53: all 1.000.**
- **devex — gold 9: 1.000 / 0.950 / 0.889 (offline); synthetic 24: all 1.000.**
- **github_actions — gold 5: 1.000 / 0.833 / 0.800 (offline); synthetic 8: all 1.000.**
- 479 tests (+18 across the UI/narration units); gate green on every PR.

**Milestone 17 status: engineering COMPLETE; NOT yet tagged.** Per spec 0112
decision 5, M17 tags only once the hosted demo is **live** — picking a host,
deploying, and recording the 2–3-minute video are the maintainer's (spend/
account). Everything not gated on hosting is landed and green.

**Next**
- **Maintainer (to close M17):** deploy `tessera-ui` (runbook in
  [`docs/DEMO.md`](DEMO.md)) and record the video; then any session tags
  `milestone-17` and hands back the **M18 kickoff** (BYO data — the
  design-partner vehicle).
- **Maintainer (unblocks the docs site):** re-enable **GitHub Pages → Source:
  GitHub Actions** in repo settings — the docs *build* is green, but the Pages
  *deploy* step 404s (`Ensure GitHub Pages has been enabled`); the setting
  lapsed. Content is fine; this is one toggle.

**Open questions / risks**
- The docs-site deploy is red on a **settings** issue (Pages source), not
  content — flagged above; does not affect the product, the gate, or any tag.
- Remaining ROADMAP2 decisions: HANA instance health, SALT HF access request,
  hosting choice (now also gates the M17 tag), BTP account, the Z Fellows
  check-in date, launch consent. Dependabot #59/#60 still open.

**State of the tree**
- `main` green and in sync; no open unit branches. PRs #126–#131 merged.
  Tagged `milestone-15` + `milestone-16`; **`milestone-17` pends the hosted
  deploy.**

---

## 2026-07-03 — Milestone 17 COMPLETE (the hosted demo is live; anyone can try it)

**The close.** The maintainer deployed the two-file Hugging Face Docker Space
(`deploy/hf-space/`, PRs #134/#135 — one YAML-limit fix hit and folded back
into the template) under his own account, card-free on the free CPU tier.
**Verified live from outside** (2026-07-03):
<https://robert-vetter-tessera.hf.space> — Space `RUNNING` on `cpu-basic`;
index 200 with the ask form + measured-floor table; the R-1042 RCA renders
verifier-checked chips; the full CSP + nosniff survive HF's proxy;
`POST /execute` returns the simulated receipt (`outcome: simulated`,
`sent: false`). The Z Fellows commitment — "a live demo anyone can try" — is
**live, working, documented**.

- README + `docs/DEMO.md` now carry the live URL; CHANGELOG rolled
  (`[milestone-17]`).
- **Milestone 17 check (spec 0112):** narration live ✓ (Unit 2); the web
  surface with 0-major reviews ✓ (Unit 3); the recorded real-agent session ✓
  (Unit 4); hosting runbook + script + one-pager ✓ (Unit 5); hosted demo
  **live** ✓ (the tag condition, decision 5). Eval byte-identical throughout;
  479 tests. **Met. Tagged `milestone-17`.**

**Next — Milestone 18 (ROADMAP2): usable on your data.**
`tessera connect github <owner/repo>` (grounded RCA over a foreign repo's real
CI failures; the design-partner pilot vehicle) + `tessera ingest <dir>`
(CSV + Markdown with declared match fields) + the "pilot in a day" runbook —
BYO paths with their own boundary tests, engine untouched. Then M19 (launch &
traction). The maintainer's 2–3-minute video over the live demo
(script: `docs/DEMO.md` §2) is the remaining M17-adjacent asset — it gates
nothing.

**Open questions / risks**
- GitHub Pages settings lapse still open (docs build green, deploy 404s) —
  one toggle: Settings → Pages → Source: GitHub Actions.
- Remaining ROADMAP2 decisions: HANA instance health, SALT HF access request
  (the maintainer now HAS the HF account — request it), BTP account, the
  Z Fellows check-in date, launch consent. Dependabot #59/#60.
- Free-tier note: the Space sleeps after ~48 h idle and wakes on visit; before
  a live presentation, open it once.

**State of the tree**
- `main` green and in sync; no open unit branches. PRs #126–#135 merged.
  **Tagged `milestone-15` + `milestone-16` + `milestone-17`.**

---

## 2026-07-03 — Milestone 18 COMPLETE (usable on your data — the BYO doors)

**Mode note:** ran autonomously from the maintainer's M18 kickoff, per CLAUDE.md
discipline — one spec per unit (spec before code), branch first, gate → PR →
CI-green → squash-merge per unit; pre-merge adversarial multi-agent review on
the two trust-bearing units; decisions recorded in specs/ADRs, not asked. The
engine stayed frozen throughout: the ADR 0008 empty-diff audit closes clean.

**Done this session (PRs #138–#142, specs 0117–0121, ADR 0028 + 0029):**
- **Plan** (spec 0117, #138): the three kickoff decision areas recorded, one
  amended by measurement — GitHub 403s **log content** on public repos without a
  token, so the optional no-scope `GITHUB_TOKEN` unlocks logs as well as raising
  rate limits (never required, never in CI, never at answer time).
- **Unit 2 — `tessera connect github` + `ask`** (spec 0118, ADR 0028, #139):
  bounded scrubbed snapshot → gitignored `var/connect/` → offline grounded RCA
  through the **unchanged** `GitHubActionsSource` + DevEx RCA, workspace-rebased
  provenance; passed/unknown runs refuse. Three-lens pre-merge review; 2 MAJORs
  + several MINORs fixed (control-sequence neutralization of all foreign text
  incl. the manifest's own miss strings; network errors → clean `ConnectError`;
  line-local scrub; TSV name/redirect hardening; more).
- **Unit 3 — `tessera smoke`** (spec 0119, #140): auto-derived per-repo
  trust-floor battery (runs-parse, failed-run-grounds, claims-supported via the
  eval's own `is_supported`, provenance-resolves, refusals-fire) + a
  recurrence-trailer WARN. Reported, never CI-gated.
- **Unit 4 — `tessera ingest <dir>` + `ask`** (spec 0120, ADR 0029, #141):
  declared `tessera.toml` (stdlib `tomllib`) → CSV + Markdown through the one
  door, multi-field ER, document-mention linking; vertical-neutral answer layer
  refuses on an **ambiguous name**. Committed public-domain demo corpus
  (`data/ingest_demo/`, a deliberate Portland OR/ME ambiguity). Three-lens
  review; 3 MAJORs fixed (template render crash, control-sequence injection,
  id/table-name collisions) + path-confinement/glob-scoping guards.
- **Unit 5 — `docs/PILOT.md`** (spec 0121, #142): the "pilot in a day" runbook
  — both BYO paths, the audit artifact, first-class honest limits; success
  criterion measured (<30 min from clone; ~20s mechanical).

**Live proof (recorded; workspaces stay local per spec 0117 decision 2):**
- `simonw/llm` (small): connect (17 req) → grounded RCA on run 28608226231
  (cog-check failure) → `smoke` all hard checks PASS + recurrence WARN.
- `astral-sh/uv` (large): connect (18 req) → grounded RCA on run 28641345176
  (cargo-test failure) → `smoke` all hard checks PASS (no recurrence WARN).
- `data/ingest_demo`: "Portland" refuses as ambiguous; "Santa Fe" returns its
  row + region (FK) + note (mention), 3 verifier-passed claims; lexical + zero-
  overlap refusal both work.
- **Honest scope:** generality claimed for exactly these two repos + the
  committed corpus. A third repo (`mkdocs/mkdocs`) had `smoke` surface a real
  `claims-supported` FAIL — the smoke battery doing its job. Diagnosed: a frozen
  `devex/rca.py` edge (the recurrence claim's anchor is `error_chunks[0]`, which
  on some logs is an error-marked chunk lacking the extracted signature, so the
  shared-fragment verifier rejects it). Deferred named future work (frozen file).

**Milestone 18 check (spec 0117):** connect+ask ✓ (Unit 2, reviewed); smoke ✓
(Unit 3, run on both corpora); ingest+ask with ambiguity refusal ✓ (Unit 4,
reviewed); PILOT.md ✓ (Unit 5); **ADR 0008 frozen-core empty-diff audit
`milestone-17..HEAD` CLEAN** (frozen list byte-identical; only new files +
the one `pyproject.toml` entry-point line); six eval lines byte-identical;
CHANGELOG `[milestone-18]`. **Met. Tagged `milestone-18`.**

**Current eval numbers (unchanged — the engine is frozen)**
- **business — gold 11: 1.000 / 1.000 / 1.000; synthetic 53: all 1.000.**
- **devex — gold 9: 1.000 / 0.950 / 0.889 (offline); synthetic 24: all 1.000.**
- **github_actions — gold 5: 1.000 / 0.833 / 0.800 (offline); synthetic 8: all 1.000.**
- 536 tests (+57 across the BYO units); gate green on every PR; CI offline/key-free.

**Next — Milestone 19 (ROADMAP2): launch & traction.** Be findable (MCP
registries), publish "The Faithfulness Floor" benchmark, Show HN + outreach to
the DACH consultancy list offering the M18 pilot, the Z Fellows check-in kit.
Kickoff prompt handed back in the session summary.

**Open questions / risks**
- **Maintainer decisions still open** (unchanged from M17): GitHub Pages source
  toggle (docs build green, deploy 404s), SALT HF access request, HANA instance
  health, BTP account, Z Fellows check-in date, launch consent. Dependabot
  #59/#60.
- The 2–3-minute demo video over the live HF Space (script `docs/DEMO.md` §2)
  remains the one M17-adjacent asset; it gates nothing.
- Named frozen-`rca.py` future work: recurrence signature (skip generic
  trailers) + recurrence anchor (cite the signature's own chunk) — both to be
  done openly in a later milestone with the batteries re-run.

**State of the tree**
- `main` green and in sync; no open unit branches. PRs #138–#142 merged.
  **Tagged `milestone-15` + `milestone-16` + `milestone-17` + `milestone-18`.**

## 2026-07-03 — Milestone 19 build share COMPLETE (launch & traction, staged; tag pends the maintainer's go)

**Mode note:** ran autonomously from the maintainer's M19 kickoff per
CLAUDE.md discipline — one spec per unit (spec before code), branch first,
gate → PR → CI-green → squash-merge per unit (PRs #144–#148, specs
0122–0126); pre-merge adversarial review on both trust-bearing units;
decisions recorded in specs, not asked. **Nothing was published or sent** —
every public act is staged for the maintainer's identity and timing (the
kickoff's hard rule; `launch/README.md` states it).

**Done this session (5 units):**
- **Unit 1 — "The Faithfulness Floor" benchmark** (spec 0122, #144, +ADR
  0007 addendum): `uv run tessera-benchmark` + `docs/BENCHMARK.md`. The
  evidence-gated engine vs its own retrieval run ungated
  (retrieve-and-recite) — same corpora, cases, verifier, claim shapes,
  scored by the harness's own `_score`. Gold trustworthy-outcome rates:
  **1.000/0.889/0.800 gated vs 0.182/0.222/0.000 ungated** (business/
  devex/gha); the ungated side's per-claim faithfulness is 1.000 by
  construction (recitation) — reported as the finding, not hidden. The
  number can fail four ways (doc-pin byte-for-byte in CI, strict
  direction pin, run_eval equality pin, the floor). Three-lens
  adversarial review (methodology skeptic / correctness / honesty): 2
  MAJORs, same wound — part of the quality gap is definitional (gold
  facts phrased by the gated engine) — resolved by **computing and
  publishing the boundary in the artifact itself** (structural notes:
  reachable-Q per battery — business synthetic 0/45, its 0.038 IS the
  ceiling and the doc says so; devex synthetic 10/10 and the baseline is
  credited 0.583), scoping the lower-bound claim to faithfulness, and
  pinning prose numbers by test.
- **Unit 2 — registry artifacts, staged** (spec 0123, #145):
  `launch/registries/` — official MCP Registry `server.json` (schema
  2025-12-11, PyPI route; **`tessera` is TAKEN on PyPI; `tessera-trust`
  staged** — dist-name + version-bump are the maintainer's decisions),
  45-minute runbook (the official registry is the upstream: PulseMCP
  auto-ingests weekly; mcp.so/awesome are satellites), blurbs, awesome
  PR line, README `mcp-name` ownership marker; CI pins keep the staged
  artifacts drift-proof (incl. version sync once pyproject leaves 0.0.0).
- **Unit 3 — launch & outreach kit, drafted** (spec 0124, #146):
  `launch/posts/` (Show HN + first comment + attack prep incl. the
  benchmark's definitional-boundary answer; r/LLMDevs; X thread) and
  `launch/outreach/` (DE/EN 4-touch DACH sequence offering the
  PILOT.md pilot; written 2-week pilot success definition; call script;
  tracking scaffold — person-level list gitignored, company rows only
  committed).
- **Unit 4 — Z Fellows check-in kit** (spec 0125, #147):
  `launch/zfellows/CHECKIN.md` — the timed 5-minute arc with live-only
  placeholders + fill sources, measured-record-bounded Q&A answers,
  offline fallback in the script. Date-independent (check-in date still
  open).
- **Unit 5 — the M18-deferred rca.py edge** (spec 0126, #148):
  recurrence signature = first **verifiable** non-generic error line
  (else first verifiable; else NO recurrence claim — never one our own
  verifier rejects); anchor = the signature's extraction chunk (the
  mkdocs smoke-FAIL class); generic trailer covers negative exit codes
  in rca + smoke's WARN together (recorded scope amendment).
  Adversarial review found 1 MAJOR in my first cut (the
  sharper-preference could pick quote-containing / normalize-to-empty
  fragments the shared-fragment grammar can't check — re-opening the
  FAIL class) + 2 MINORs + 1 NIT; all fixed, eight foreign-log fixtures
  pin the shapes (the two core ones demonstrated failing on the old
  code). **Output-neutral on committed corpora, proven twice** —
  byte-identical renders of every committed failed run, independently
  reproduced in review.

**Current eval numbers (unchanged — byte-identical throughout):**
- **business — gold 11: 1.000 / 1.000 / 1.000; synthetic 53: all 1.000.**
- **devex — gold 9: 1.000 / 0.950 / 0.889 (offline); synthetic 24: all 1.000.**
- **github_actions — gold 5: 1.000 / 0.833 / 0.800 (offline); synthetic 8: all 1.000.**
- New, separately-published benchmark numbers live in `docs/BENCHMARK.md`
  (CI-pinned). 557 tests (+21 this milestone); gate green on every PR.

**Milestone 19 check (kickoff + ROADMAP2):** benchmark published in-repo,
able to fail ✓ (Unit 1); findable = staged submissions + runbook ✓ (Unit
2; submission itself is the maintainer's); launch + outreach drafted ✓
(Unit 3); Z Fellows kit ✓ (Unit 4); the deferred rca edge folded in
openly with batteries re-run and proven neutral ✓ (Unit 5). **ADR 0008
frozen-core empty-diff audit `milestone-18..HEAD` CLEAN** (three source
files touched all milestone: new `eval/benchmark.py`, vertical
`devex/rca.py`, one regex token in `connect/smoke.py`); hosted demo, UI,
MCP, BYO doors untouched. **The `milestone-19` tag PENDS the
maintainer's public acts** — ROADMAP2's done-when includes "launched"
and "outreach sent" (M17 precedent: tag when the milestone condition is
met, not when the code is).

**Next — the maintainer's go-list (everything staged; "go" costs minutes):**
1. **Registries** (`launch/registries/RUNBOOK.md`, ~45 min): decide the
   PyPI dist name (`tessera` is taken; `tessera-trust` staged) + first
   version (0.1.0 staged); publish to PyPI → `mcp-publisher` → claims →
   awesome PR.
2. **Launch** (`launch/posts/`): re-run `tessera-benchmark`, warm the HF
   Space, post Show HN + satellites on your timing; stay in-thread 3–4h.
3. **Outreach** (`launch/outreach/`): fill `targets.csv` (gitignored),
   send wave 1, work the 4-touch sequence toward ≥2 design-partner
   pilots.
4. **Z Fellows** (`launch/zfellows/CHECKIN.md`): confirm the check-in
   date, fill the placeholders that morning, rehearse twice.
5. Then any session tags `milestone-19` and rolls the CHANGELOG section.
6. Standing items (unchanged): the 2–3-min demo video (script DEMO.md
   §2; gates nothing), GitHub Pages source toggle (docs deploy 404s),
   SALT HF access request, HANA instance health, BTP account,
   dependabot #59/#60.

**Open questions / risks**
- The official MCP Registry is in preview (schema/reset risk recorded in
  the runbook; `server.json` pins schema 2025-12-11 so mismatch fails
  loudly at publish).
- The benchmark invites attack by design — expect (and welcome)
  methodology issues after launch; the attack surface is documented and
  the honest answers are staged in the launch kit.
- `The operation was canceled.` is another information-free runner line
  outside the generic-trailer set (review note, semantics-adjacent,
  recorded in spec 0126 — future work if smoke shows it mattering).

**State of the tree**
- `main` green and in sync; no open unit branches. PRs #144–#148 merged.
  Tagged through `milestone-18`; **`milestone-19` pends launch**.

## 2026-07-03 — SAP track: S4 + S2 shipped (the post-M19 build surface)

**Mode note:** ran autonomously from the maintainer's "keep building —
continue with the plan" after the M19 build share. The remaining ROADMAP2
surface is the SAP track; scope fixed on measured facts in the plan spec
(0127, PR #150) before any unit code. Discipline unchanged: spec → branch
→ gate → PR → CI-green → squash-merge; the trust-adjacent unit carried a
pre-merge adversarial review.

**Done this session (3 units, PRs #150–#152, specs 0127–0129, ADR 0030):**
- **Plan** (spec 0127, #150): probed the M6/M7 HANA instance with the
  existing `.env` keys (the ROADMAP2 maintainer checklist itself asks for
  the health check): **alive**, cloud version 2026.14.7 — but the KG
  **triple store is not enabled** (`SYS.SPARQL_EXECUTE` answers "No
  active TripleStore found in landscape"); enablement is the account
  owner's HANA Cloud Central → Advanced Settings → **Triple Store**
  checkbox. Decisions: S2 ships the full seam now with the online run
  one toggle away (the M17 Pages-toggle pattern); persistence is a
  mirror, never a source of truth; S4 in `launch/sap/`; S1 stays blocked
  on the SALT/HF access request; S3 stays a spend decision.
- **S4 — the application kit** (spec 0128, #151):
  `launch/sap/APPLICATION.md` — both German tracks (EN iXp + DE
  Werkstudent letters, opening on the SAP-sponsored
  Deutschlandstipendium), the Sapphire-2026 mapping table (Agent Hub
  "verification badges" ↔ a *measured* faithfulness score; Claude-via-MCP
  ↔ the recorded agent session; DSAG 3% hook), target teams (BTP AI
  Core/GenAI Hub, Joule Studio, Business AI research, Prior Labs),
  artifact links, CV bullets, submission checklist. `SAP_ALIGNMENT.md`
  gained a dated addendum fixing its one stale beat honestly: the
  agentic/MCP mode it *recommends* shipped months ago (ADR 0022–0025).
- **S2 — HANA KG persistence** (spec 0129, ADR 0030, #152):
  `tessera/platform/kg.py` — the graph as RDF over `SPARQL_EXECUTE`
  (structure as triples incl. reified reversible resolutions/mentions;
  provenance as byte-exact literals; untyped repr floats), one named
  graph per corpus, DROP+batched-INSERT idempotent mirror.
  **Losslessness tested**: serializer → subset parser → rebuild
  tuple-exact on all three committed graphs; duplicate edges fail
  loudly; injection-safe escaping. Adversarial review found 1 MAJOR
  (`splitlines()` splits on U+2028/U+2029/U+0085 the escaper left raw —
  fixed twice over: escaped AND \n-only split) + 1 MINOR (the SPARQL
  §19.2 pre-parse hazard — no clean in-band escape exists, so the staged
  one-shot now opens with an **escape-fidelity canary** whose verdict is
  recorded verbatim) + 3 NITs (password-bearing config out of repr;
  robust COUNT alias; mentions query joins through resolutions), all
  fixed and pinned. `HanaTripleStore` fake-contract-tested; hdbcli stays
  the lazy `cloud` extra (import-guard); CI key-free.

**Current eval numbers (unchanged — byte-identical throughout):**
- **business — gold 11: 1.000 / 1.000 / 1.000; synthetic 53: all 1.000.**
- **devex — gold 9: 1.000 / 0.950 / 0.889 (offline); synthetic 24: all 1.000.**
- **github_actions — gold 5: 1.000 / 0.833 / 0.800 (offline); synthetic 8: all 1.000.**
- 567 tests (+10); frozen core untouched (the milestone's source diff:
  `platform/kg.py` new, plus the M19-session files).

**Next — the maintainer's items:**
1. **NEW — the Triple Store toggle** (~2 min, may restart the instance:
   HANA Cloud Central → instance → Manage Configuration → Advanced
   Settings → Triple Store), then
   `uv run python scripts/persist_knowledge_graph.py` and paste its
   record block (incl. the canary verdict) into DEPLOYMENT.md — that
   turns "designed for SAP Knowledge Graph" into "ran on", beside the
   recorded `VECTOR_EMBEDDING` closes.
2. **M19 go-list unchanged:** registries runbook (2 decisions), launch
   posts, outreach wave, Z Fellows date + rehearse (the first weekly
   ship-update email is drafted in the session transcript), then tag
   `milestone-19` + roll the CHANGELOG.
3. Standing: SALT HF access request (gates S1 — the highest-credibility
   remaining S-track item), demo video, Pages source toggle, BTP
   (gates S3), dependabot #59/#133 (#60 closed).

**Open questions / risks**
- `result[2]` as `SPARQL_EXECUTE`'s response OUT parameter is
  tutorial-verified, not yet live-verified (the probe errored before OUT
  extraction, correctly — no TripleStore); the one-shot is the honest
  first check and records whatever happens.
- The KG engine is young (GA QRC1 2025); the escape-fidelity canary
  exists precisely because store-side literal handling may diverge from
  the spec reading.

**State of the tree**
- `main` green and in sync; no open unit branches. PRs #150–#152 merged.
  Tags unchanged (through `milestone-18`; `milestone-19` pends launch;
  the SAP track carries no tag).

## 2026-07-04 — S2 online run: the measured tier boundary (KG engine is not on free tier)

**What happened.** The maintainer attempted the staged S2 one-shot. The
diagnosis chain, each step measured: (1) the overnight connect failure was
the free tier's auto-stop, not the toggle-restart — the instance came back
9 minutes after Start and answered SQL; (2) `SPARQL_EXECUTE` still said
"No active TripleStore found in landscape"; (3) `M_INIFILE_CONTENTS` has
**no** triple-store entry and only the four baseline services run — the
setting never landed; (4) the maintainer's Advanced Settings screenshot
shows **no Triple Store option at all**, with the banner "Not all advanced
options are available for free tier instances"; (5) verified against SAP's
license documentation: **the knowledge graph engine is not supported on
free-tier instances** (needs a paid configuration, ≥3 vCPUs / 45 GB; BTP
trial equally gated). There was never a checkbox to find.

**What changed in the repo (this entry's PR):** DEPLOYMENT.md's KG section
now records the tier boundary (the paid-instance path stays as the
runbook); the "one toggle away" phrasing corrected everywhere it appeared
(SAP_ALIGNMENT addendum, launch/sap/APPLICATION.md incl. both cover
letters — no sentence now claims the KG mirror "ran"); CHANGELOG
[Unreleased] updated. The seam, tests, and the staged one-shot are
unchanged and remain ready.

**The decision now on the record (maintainer's, spend-class like S3):**
- **Upgrade to a paid tier** for one measurement window (pay-as-you-go +
  stopped-when-idle keeps a one-shot cheap; rates in the BTP estimator) →
  run `scripts/persist_knowledge_graph.py` → paste the record (incl. the
  escape-fidelity canary verdict) into DEPLOYMENT.md — "ran on SAP
  Knowledge Graph" becomes literal.
- **Or stand pat:** the honest posture — seam contract-tested, procedure
  signature verified against the live instance, store tier-gated — is
  itself a credible SAP-application line, and the free-tier
  `VECTOR_EMBEDDING` closes remain the recorded "ran on SAP" proof.

**Eval:** untouched (docs-only session; six lines byte-identical).

**State of the tree:** `main` green; this correction is the only change.
Tags unchanged.

## 2026-07-04 — S2 online: closed as tier-gated (decision recorded)

The paid-tier path is off: pay-as-you-go is not offered to this account
class without an enterprise sales contact, which the maintainer declined.
Decision recorded (DEPLOYMENT.md "Recorded run" note): **S2 stands pat on
the honest posture** — seam contract-tested, procedure signature
live-verified, store tier-gated; the free-tier `VECTOR_EMBEDDING` closes
remain the recorded "ran on SAP" proof. The runbook and staged one-shot
stay in place unchanged should a paid instance ever materialize. The SAP
track's build surface is now fully closed; S1 still awaits only the SALT
HF access request (free, one click + approval lead time), S3 remains a
non-plan (same account-class constraint). Docs-only; eval untouched.

## 2026-07-04 — SAP track S1 SHIPPED: Tessera runs on the real gated SALT dataset

**Mode note:** the maintainer's gated HF access arrived (token in `.env`);
the dataset was pulled to gitignored `var/salt_real/` (116 MB, 8 parquet
tables). The shaping decision was his ("build what really applies"); the
unit ran per discipline: spec 0130 before code, branch, focused pre-merge
review, gate, PR #156.

**The headline finding (measured, in the report):** real SALT is **fully
anonymized** — `I_Customer` is code+address-id (no name);
`I_AddrOrgNamePostalAddress`'s name column is empty on **all 1,788,887
rows**; across all 8 tables there is no free-text name/street/city
anywhere; linkage is exact foreign key. Consequence, recorded not hidden:
**name-similarity ER has no real-SALT analog** (the synthetic corpus
*invented* names to exercise it) — real SALT's difficulty is **relational,
not lexical**, which is the SALT-KG thesis confirmed on the data, and the
strongest honest line for the SAP application.

**What shipped (PR #156, spec 0130):**
- `scripts/salt_real_slice.py` (opt-in `salt` extra / pyarrow):
  deterministic connected slice — 25 real customers (connected universe:
  13,155, printed by the script), their addresses, 59 sales docs, 115
  items → CSV in gitignored `var/salt_real_slice/`.
- `tessera/sources/salt_real.py` (stdlib): ingests the slice into the
  UNCHANGED engine — Customer/Address/SalesDoc/SalesItem nodes, exact-FK
  edges (`located_at`/`sold_to`/`line_of`); `describe_customer` composes
  customer + address + docs, each claim citing a real SALT row; unknown
  code refuses; every field control-neutralized; malformed slices fail
  with file+columns named.
- **Recorded real run** (`docs/SALT_REAL.md`): 224 records, 255 edges;
  **faithfulness 109/109 = 1.000 by the eval's own `is_supported`
  (structural containment, caveat stated); 0 dangling citations.**
- CI floor: `tests/test_salt_real.py` (7) over the authored anonymized
  fixture `data/salt_real_fixture/` — no gated data, no pyarrow in CI.
- Review (1 MAJOR + 1 MINOR + 3 NITs, all fixed): the MAJOR was verbatim
  real rows in the report draft — SALT is CC-BY-NC-SA + gated vs the MIT
  repo, and the NOTICE promises "not redistributed here"; the report now
  carries statistics + the fixture-shaped example only.

**Eval:** six lines byte-identical; frozen core + `sources/salt.py`
untouched; 568 tests.

**SAP track status:** S1 ✓ (this) · S2 seam ✓ / online tier-gated,
stand-pat recorded (#155) · S3 non-plan (account class) · S4 kit ✓ —
**the S-track is now fully closed on the build side.** APPLICATION.md's
SALT line upgraded to the measured reality (with the containment
qualifier).

**Next:** unchanged — the maintainer's M19 launch acts (registries →
Show HN → outreach → Z Fellows date → tag milestone-19). The SALT finding
is fresh material for both the SAP letters (already woven in) and the
next Z Fellows ship-update.

**State of the tree:** `main` green after #156; no open unit branches;
tags through `milestone-18` (`milestone-19` pends launch).
