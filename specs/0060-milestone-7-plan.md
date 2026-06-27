# 0060. Milestone 7 plan: embeddings beyond retrieval — entity resolution + de-diluted logs

- **Phase / milestone:** Milestone 7 — Embeddings applied to ER and log
  granularity (post-roadmap; ROADMAP phases complete and tagged `phase-0`…
  `phase-4`; hardening `milestone-5`; embeddings-on-SAP `milestone-6`)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018: decisions recorded here
  instead of asked — except the three project-shaping questions below, which were
  asked and answered 2026-06-27)

## Problem

Milestone 6 brought real SAP HANA embeddings into the engine and closed the
undeclarable error-class-synonymy miss — but deliberately confined embeddings to
**retrieval only**. Two named limitations were left standing in the M6 close
(`docs/STATUS.md`, ADR 0015 addendum):

1. **Entity resolution never saw an embedding.** ER is still pure-`difflib`
   character similarity at a 0.85 threshold (`tessera/resolution.py`,
   `KnowledgeGraph.resolve_entities`). Two specimens are recorded and unfixed:
   - `checkout-service ↔ checkout-svc` = **0.846** — a recall **miss** (just under
     the threshold; an abbreviation gap character-similarity can't bridge), kept
     as the named near-miss (`tests/test_devex_graph.py`).
   - The generic-suffix firms (`… Logistik GmbH`) **over-merge** at volume — a
     precision **error** measured as a fact in `tests/test_scale.py` (Granite/
     Pyrite/Cobalt/Basalt collapse because the shared suffix dominates the
     character ratio).

2. **Long-document dilution.** The real Pages-deploy log ingests as **one
   61-line chunk** (`tessera/sources/github_actions.py`, `parse_log_chunks`
   groups by `(job, step)` and the runner log is a single stream). The specific
   `404` lines sit at lines 50–57 behind ~49 lines of provisioning boilerplate
   (~7× the concise run-status row), so even with embeddings the synonymy answer
   surfaces the failed **run**, not the **404 line** (spec 0058 corrected gold-05
   to expect the run row as the honest compromise).

These are opposite-signed and complementary: ER needs embeddings to add a
**recall** signal where character similarity is blind (`checkout-svc`) **and** a
**precision** signal where character similarity over-fires (generic suffix);
logs need finer **granularity** so the de-dilution embeddings already pay for
actually surfaces the failing line. Both are the natural M6 follow-through:
*apply the working embeddings beyond retrieval-only, and keep faithfulness gated
at 1.0 and embedding-free on the claim path the whole time.*

The central honesty hazard is that **the two ER cases pull in opposite
directions.** A naive name-cosine pass closes `checkout-svc` but makes the
generic-suffix over-merge *worse* (`Granite Logistik GmbH` and `Pyrite Logistik
GmbH` are semantically near-identical: same industry token + legal form). So a
method that fixes recall by costing precision is a **recorded finding that fires
a fresh trigger**, not a silently-tuned number (the ADR 0015 "earned, not a
re-saturation" rule, applied to ER).

**Maintainer decisions (asked 2026-06-27, because they are project-shaping):**

1. **Online HANA re-measurement — yes.** The wins (embedding-bridged ER recall;
   the de-diluted 404 line) only materialize on the semantic/HANA path; offline
   lexical/`difflib` cannot bridge them by construction. The maintainer will run
   the one-shot `tessera-eval --record` on SAP HANA Cloud (instance + the
   `TESSERA.TESSERA_DOC_VECTORS` table persist from M6) and the real numbers land
   as **timestamped points** in `eval/history.jsonl`. "Ran on SAP" continues.
2. **ER scope — close recall + attempt over-merge, record residual.** Pursue both
   named cases: bridge the `checkout-svc` abbreviation gap (recall) **and** attack
   the generic-suffix over-merge (precision), using the **distinctive stem**
   (suffix-stripped) plus a **conjunction gate** so an embedding edge is asserted
   only when it adds a real signal, never on the generic suffix alone. If a single
   rule cannot satisfy both without regressing the precision tests, the residual
   is **recorded as a measured finding + a fresh trigger** (the Milestone-5
   keep-the-miss precedent), not forced.
3. **Both threads, ER first.** One milestone: embedding-assisted ER (the headline)
   then finer log chunking (the de-dilution). Cohesive — both are "embeddings
   beyond retrieval-only."

## Success criterion

Milestone 6 closed a **retrieval** miss with embeddings. Milestone 7 carries the
same method into the **two places M6 explicitly deferred** — entity resolution
and log granularity — and is honest about which gains are real:

- **The `checkout-svc` recall miss is closed by a semantic name signal**, and the
  close is **earned**: the same embedding pass must **not** over-merge distinct
  services (the ADR 0015 precision guard, now applied to ER) and must **not**
  worsen the generic-suffix over-merge. Recall **and** precision are both
  measured and reported; an over-merge is a recorded finding, never hidden.
- **The generic-suffix over-merge is attacked, and the outcome is recorded
  honestly** — closed if the stem+conjunction design closes it without precision
  loss; otherwise kept as a measured residual with a fresh, named trigger.
- **The de-diluted log surfaces the actual `404` line, not just the failed run.**
  Finer chunking isolates the `##[error]` cluster into its own short chunk;
  gold-05 can then legitimately expect that chunk on the semantic path. The
  offline/lexical path stays the honest miss (the question shares zero tokens with
  the log), so CI's public number is unchanged.
- **Faithfulness stays gated at 1.0 throughout, never weakened or re-defined.**
  ER and chunking change *what is surfaced/linked*, never *what is claimed*:
  `eval/metrics.py` (`is_supported`) stays deterministic, structural, and
  **embedding-free** (the leak-guard test holds; the new ER-embedding module is
  added to its banned set and kept out of the verifier's import closure). An ER
  change that re-clusters entities re-flows through the verifier, which recomputes
  superlative/compare over the new graph — composition and verification must
  agree on the same graph, or the floor catches it (as intended).
- **CI stays key-free and offline on the deterministic path.** `difflib` ER and
  lexical retrieval are unchanged when `TESSERA_EMBEDDINGS=none`; `hdbcli` stays
  the opt-in `cloud` extra. The embedding ER/log gains are **timestamped one-time
  online measurements** (the M5/M6 precedent), not CI-reproducible numbers,
  stated as such wherever they appear.
- **The mechanism is CI-reproducible even though the cloud number is not.** A
  **seeded in-memory stub embedder** drives a deterministic ER precision/recall
  test and a deterministic semantic-retrieval test, so the *wiring and the
  precision guards* are proven offline; only the *real model's judgment* needs the
  online run.
- If the online run cannot honestly move a number, that is **reported plainly**,
  and the milestone ends with the seam built + a recorded residual rather than a
  fabricated 1.000.

## Acceptance criteria

- [ ] **ER embedding seam (offline-deterministic).** A new module (e.g.
      `tessera/er_semantic.py`) proposes additive `Resolution`s from an embedding
      signal: for org-name pairs it requires a high **stem** cosine **and** a
      conjunction gate (a non-generic shared signal), reusing the existing
      `SemanticRetriever`/`VectorStore` seam. It is **never** imported by
      `eval/metrics.py` or anything in the verifier's closure
      (`graph`/`grounding`/`resolution`); the leak-guard banned set gains the new
      module name. A **seeded in-memory stub embedder** makes the path
      deterministic offline. **ADR 0016** records the design (stem + conjunction,
      additive/reversible, vertical-side application).
- [ ] **ER precision/recall measurement.** A deterministic harness over a
      **labeled pair set** — `checkout-svc` should-merge; the generic-suffix
      cohort and `Müller Logistik` ≠ `Nordwind Logistik` should-**not**-merge;
      accented variants should-merge — reports precision/recall for the baseline
      `difflib` pass and the embedding-assisted pass (stub embedder, so
      CI-reproducible). Faithfulness stays the only hard gate; ER precision/recall
      is a reported measurement, not a new CI floor.
- [ ] **Apply to the devex graph, recall closed + over-merge attempted.** The
      embedding ER pass is wired **vertical-side** (mirroring
      `devex/knowledge.py::_assert_declared_aliases`, never inside the engine
      `resolve_entities`) behind `TESSERA_EMBEDDINGS`. With embeddings active,
      `checkout-service ↔ checkout-svc` resolves (recall close); distinct services
      stay unlinked (precision held); the generic-suffix outcome is measured and
      its residual recorded. The default (`none`) path is byte-identical to today.
      Faithfulness 1.0 on every battery.
- [ ] **Finer log chunking + stable chunk-id contract.** `parse_log_chunks`
      sub-divides a `(job, step)` group to isolate the `##[error]` cluster into its
      own short chunk with a correct sub-line-range locator; chunk ids become
      **stable and content/section-derived** (not positional) so committed gold
      ids survive re-chunking. gold-02 expectations, `structural_edges`, and the
      affected tests are updated; offline lexical numbers stay green. **ADR 0017**
      records the id contract.
- [ ] **De-diluted synonymy gold-05.** With the error cluster isolated, gold-05's
      `expected_support` points at the focused `##[error]` chunk; on the semantic
      path the answer surfaces the `404` line. The offline/lexical path remains the
      honest miss; CI's public coverage number is unchanged. The precision guard
      (no over-link) is intact.
- [ ] **The online measurement(s) (spend, maintainer-confirmed).** The maintainer
      runs `tessera-eval --record` online once on HANA, producing the embedding ER
      recall close **and** the de-diluted log close as timestamped points in
      `eval/history.jsonl` (faithfulness 1.0). A `--recorded` flag is added if a
      precise timestamp is wanted; otherwise the existing one-shot is reused
      verbatim.
- [ ] **Close.** Gate green under multiple `PYTHONHASHSEED` values (offline path);
      WRITEUP "embeddings beyond retrieval" section citing the recorded numbers and
      any honest residual; README numbers; CHANGELOG `[milestone-7]`; STATUS;
      empty-diff core check (ADR 0008) for the engine; tag `milestone-7`; memory;
      next-milestone kickoff handed back.

## Scope

**In — the unit breakdown (one PR each, spec each):**

| Unit | Spec | Content |
|---|---|---|
| 1 | 0060 | this plan + the three recorded scope decisions |
| 2 | 0061 | ER embedding seam: new `tessera/er_semantic.py` (stem cosine + conjunction gate → additive `Resolution`s), seeded in-memory stub embedder, leak-guard banned-set extension; **ADR 0016** (embedding-assisted ER design) |
| 3 | 0062 | deterministic ER precision/recall harness over a labeled pair set (baseline `difflib` vs embedding-assisted, stub embedder); reported not gated |
| 4 | 0063 | apply vertical-side to the devex graph: close `checkout-svc` recall, measure generic-suffix precision, record residual; faithfulness 1.0; `none` path byte-identical |
| 5 | 0064 | finer log chunking — isolate the `##[error]` cluster; stable content-derived chunk ids; gold-02/`structural_edges`/tests updated; offline numbers green; **ADR 0017** (chunk-id contract) |
| 6 | 0065 | de-diluted gold-05 (semantic path surfaces the 404 line; offline lexical stays the honest miss; precision guard intact) |
| 7 | 0066 | the online HANA measurement(s) — prep + `--recorded` flag if wanted; maintainer runs once; record timestamped points |
| 8 | 0067 | close: WRITEUP/README/CHANGELOG/STATUS, empty-diff core check, tag `milestone-7`, memory, kickoff |

**Out (explicitly):**

- **Multi-field ER (name + address/attributes).** The maintainer chose the
  embedding route (option A), not the multi-field lever (option C). Multi-field
  matching stays ADR 0004 future work; if stem-embedding + conjunction cannot
  close the generic-suffix over-merge, that is the recorded residual and
  multi-field is named as the candidate next lever — not built here.
- **Embeddings on the claim / faithfulness path.** `is_supported` stays
  deterministic and structural; ADR 0005's LLM-judge stays deferred. Embeddings
  serve retrieval/linking/ER only.
- **A new gated eval metric for ER.** Faithfulness remains the single hard CI
  floor. ER precision/recall is a reported measurement (a test + an optional
  recorded note), not a new gate, to avoid pulling cloud into CI and to keep the
  floor's definition transparent.
- **HANA as general graph persistence.** Only the existing vector path is reused;
  the graph stays the embedded in-process `KnowledgeGraph` (ADR 0004).
- A **second real connector**; **agentic/MCP** mode; persistence/multi-tenancy/
  security hardening. These remain the WRITEUP's named future work.

## Eval impact

- **ER recall up (online):** `checkout-service ↔ checkout-svc` moves miss → close
  via a semantic name signal; recorded online in `eval/history.jsonl`. The
  mechanism (and that the close is *earned*) is proven offline with the stub
  embedder; the *real model's* recall is the online point.
- **ER precision measured (offline + online):** distinct services and the
  generic-suffix cohort are checked to stay unlinked; reported alongside recall.
  Any over-merge is a recorded finding, not hidden.
- **Coverage up (online):** the de-diluted gold-05 surfaces the `404` line on the
  semantic path (offline lexical still records the honest miss — both points
  kept). CI's public coverage number is unchanged.
- **Faithfulness pinned at 1.0** at every recorded point. Any drop is a real bug
  (embeddings must not leak into claims, and re-clustering must not desync
  composition from verification), never a new normal.
- **Offline numbers unchanged** on the deterministic path CI runs; the default
  batteries read exactly as Milestone 6 left them.

## Risks / open questions

- **The opposite-direction ER tension (the central technical risk).** Recall
  (`checkout-svc`, merge more) and precision (generic suffix, merge less) pull
  apart. The design answer is to embed the **distinctive stem** and require a
  **conjunction** (high stem cosine AND a non-generic shared signal), so the
  generic suffix alone never triggers a merge. If no single rule satisfies both
  against the precision tests (`test_scale.py` 180→180 clusters; Müller ≠
  Nordwind), the honest answer is a recorded residual + fresh trigger
  (multi-field ER named as the next lever) — ADR 0016 must make this crisp.
- **Faithfulness re-cluster risk.** Embedding-assisted ER changes
  `graph.clusters()`/`entity_of`, which the business verifier shapes recompute
  over (`business/claims.py`). If ER over-merges, a superlative/compare claim's
  recomputed winner/total can diverge from the stated text → `is_supported`
  returns False → the floor breaks. That is the verifier catching a real
  composition error; the fix is to keep composition and verification on the same
  graph, never to relax the shape. Business `uses_semantic` stays **False** by
  default so business ER is untouched offline; the ER-embedding application is
  scoped to where it is measured.
- **Leak-guard breach risk.** The most likely accidental breach is an
  `import` of an embedding/vector module into `resolution.py` (which the verifier
  transitively imports via `normalize`). The ER-embedding logic must live in a
  **separate** module, consume the graph/names as data, and write back only
  additive `Resolution`s — `graph`/`resolution`/`grounding`/`metrics` stay
  stdlib-only. The leak-guard banned set gains the new module name so a future
  edit that makes it reachable fails loudly.
- **Chunk-id renumbering (the log risk).** Ids are positional today
  (`{run_id}.failed:chunk{index}`) and committed gold cases pin them (gold-02
  pins two `:chunk1` ids with `HttpError: Not Found` among `expected_facts`).
  Re-chunking renames records and redistributes error text. The fix is a
  **stable content/section-derived id** (ADR 0017); gold-02's expectations and
  any chunk-count/`structural_edges` tests move with it. Over-fine chunking that
  drops a chunk below `score > 0` is the opposite failure — guard the error
  cluster stays a usable size.
- **Online non-reproducibility.** The cloud model (`SAP_NEB.20240715`) can change
  or be retired; the recorded online numbers are point-in-time artifacts, labeled
  so in their notes, never promoted to the gated/public number. CI's public
  numbers stay the deterministic offline ones.
- **Cost / security.** Each online run embeds a few hundred short texts + a
  handful of KNN queries — small; confirm per-run cost before the U7 run; do not
  loop the online eval. `.env` stays gitignored; gitleaks guards commits; the
  documented least-privilege `TESSERA_APP` user is the recommended production
  setup (the M6 `DBADMIN` run is noted, rotation recommended).
- **Engine-generality.** The ER-embedding *application* (which names, which
  battery) stays vertical-side, mirroring the declared-alias precedent; the engine
  `resolve_entities` and `KnowledgeGraph` stay vertical-neutral and embedding-free.
  Guarded by the empty-diff core check at close (ADR 0008).
