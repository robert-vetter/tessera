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
