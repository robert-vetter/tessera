# 0068. Milestone 8 plan: cure the generic-suffix over-merge (deterministic stem-gated ER)

- **Phase / milestone:** Milestone 8 — Deterministic ER precision: cure the
  generic-suffix over-merge (post-roadmap; ROADMAP phases complete and tagged
  `phase-0`…`phase-4`; hardening `milestone-5`; embeddings-on-SAP `milestone-6`;
  embeddings-beyond-retrieval `milestone-7`)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018: decisions recorded here
  instead of asked — except the two project-shaping scope questions below, which
  were asked and answered 2026-06-28)

## Problem

Milestone 7 carried embeddings into entity resolution as a **second, additive**
regime (`tessera/er_semantic.py`, ADR 0016): it closed the `checkout-svc` recall
miss, but — because it is *additive* — it could not remove the **other**, longer-
standing ER defect, and recorded the residual explicitly:

> the union's precision gap is **entirely** difflib's pre-existing generic-suffix
> over-merge … an *additive* embedding regime cannot remove a difflib false
> positive (`tests/test_er_metrics.py`).

The defect: the **deterministic** core pass, `KnowledgeGraph.resolve_entities`
([`src/tessera/graph.py`](../src/tessera/graph.py)), asserts a merge whenever
`difflib.SequenceMatcher` over the **full normalized names** clears 0.85. When the
shared part of two names is a long *generic* suffix, that suffix dominates the
character ratio and distinct firms collapse — measured as a fact in
`tests/test_scale.py`:

- `Granite Logistik GmbH` ~ `Pyrite Logistik GmbH` = 0.865 → over-merge
- `Cobalt Logistik GmbH` ~ `Basalt Logistik GmbH` = 0.889 → over-merge

So difflib precision sits at **0.50** on the labelled pair set and the union at
**0.67** (`test_er_metrics.py`), and `test_scale.py` *asserts the over-merge* as a
named limitation. M7's STATUS, ADR 0016, and the `test_er_metrics` docstring all
name the same next lever:

> apply the same stem-gating to the **difflib** pass (a deterministic engine
> change that would alter `resolve_entities`/`test_scale`) — or multi-field ER.

This milestone takes that lever. It is **deterministic, offline, CI-reproducible**
— no cloud, no online run — and it is the inverse of M7's additive embedding move:
where M7 *added* merges (recall), M8 *removes* over-merges (precision), in the core
pass, with the cure provable in CI.

**Maintainer decisions (asked 2026-06-28, because they are project-shaping):**

1. **Lever scope — stem-gate the `difflib` pass only.** Not multi-field ER (the
   stronger but larger ADR 0004 lever). Surgical, fully CI-reproducible, reuses the
   M7 stem machinery, drives difflib precision to 1.0 on the measured pair set.
   Multi-field ER stays the named next lever for the residual (below).
2. **Honesty posture — keep a new measured edge.** Stem-gating cures the
   *generic-suffix* collision but is not perfect: it cannot separate two **distinct
   firms whose names are character-near-identical** (they share the distinctive
   token; only address/keys would tell them apart). Replace the cured `test_scale`
   specimen with that harder case, recorded as the next revisit trigger pointing at
   multi-field ER — preserving the Milestone-5 "the eval can still fail" discipline.

## The design (the one technical decision, recorded for ADR 0018)

A merge asserted by `resolve_entities` at/above the 0.85 character threshold is
**confirmed only if the two names also share a *distinctive* token** — a non-generic
token, matched typo-tolerantly. This is a **conjunctive tightening** of the existing
pass: it can only *remove* merges, never add one, so the only mergers it can drop
are those carried purely by shared generic tokens — exactly the over-merges.

- *Distinctive* = a token that is **not generic**. Generic = the M7 stoplist:
  universal org descriptors (`service`/`svc`/`system`/…) ∪ legal forms
  (`LEGAL_SUFFIXES`) ∪ tokens whose **corpus document frequency** is at/above the
  named cutoff (so `Logistik` across four firms becomes generic without anyone
  naming it). Reused verbatim from `er_semantic.py`.
- *Shared, typo-tolerant* = some distinctive token of A is `>=` the threshold
  difflib-similar to some distinctive token of B (existential, not holistic).

Why **existential shared-token**, not **holistic stem similarity** (the obvious
first reading of "stem-gate"): a holistic `similarity(stem_a, stem_b)` gate **breaks
a correct merge**. `search-service` ↔ `search-servce` is a real typo merge, but the
typo `servce` is not recognised as a generic descriptor, so the stems become
`"search"` vs `"search servce"` (~0.67) and the gate would wrongly reject it. The
existential rule is robust to typos in generic tokens: it only needs *one* shared
distinctive token (`search` ~ `search` = 1.0), which is precisely the signal that
two records name the same firm.

Worked outcomes (all preserved / cured as intended):

| pair | full sim | shared distinctive token? | outcome |
|---|---|---|---|
| `Granite Logistik GmbH` / `Pyrite Logistik GmbH` | 0.865 | `granite`≁`pyrite` → **no** | **over-merge cured** |
| `Cobalt Logistik GmbH` / `Basalt Logistik GmbH` | 0.889 | `cobalt`≁`basalt` → **no** | **over-merge cured** |
| `Bayerische …` / `Bayersche …` (typo) | ~0.95 | `stahlwerke`=`stahlwerke` → yes | merge preserved |
| `search-service` / `search-servce` (typo) | 0.960 | `search`=`search` → yes | merge preserved |
| `payments-service` / `Payments Service` | 1.000 | `payments`=`payments` → yes | merge preserved |
| `Müller Logistik GmbH` / `Mueller …` addr | high | `mueller`=`mueller` → yes | merge preserved |

The cure needs no embedding and no cloud — the distinctive-stem machinery is
pure-stdlib deterministic string work. It **does touch the frozen core**
(`graph.py`/`resolution.py`, ADR 0008's empty-diff list): a *general* ER precision
improvement legitimately belongs in the core, not a vertical. That intentional
exception is recorded in **ADR 0018** and noted at the M8 empty-diff check.

## Success criterion

The generic-suffix over-merge — recorded as an unfixable residual at the end of M7 —
is **cured in the core deterministic ER pass, provably in CI**:

- difflib precision on the labelled pair set moves **0.50 → 1.00**, the union
  **0.67 → 1.00**; `test_scale`'s generic-suffix specimen flips from *asserting the
  over-merge* to *asserting four distinct firms → four clusters*.
- **No correct merge is lost.** Every real merge in the business and devex demo
  graphs (Bayerische 4-way, Müller customer↔address, the catalog↔on-call variants,
  the accented cohort) survives, *measured* — all three batteries read byte-identical
  to M7 (faithfulness 1.0, coverage/quality unchanged).
- **A new, harder over-merge edge is planted and recorded** — two distinct firms
  with character-near-identical names that stem-gating correctly cannot separate —
  with multi-field ER named as its next lever (the kept-a-measured-edge posture).
- **Faithfulness stays the single hard gate, structural and embedding-free.** The
  leak-guard holds: the stem helpers move to `resolution.py` (already verifier-
  reachable and embedding-free), never pulling an embedding import toward the
  verifier; `eval/metrics.py` is untouched.
- **CI stays offline/deterministic/key-free.** This whole milestone is reproducible
  in CI; there is **no online run** (unlike M6/M7).

## Acceptance criteria

- [ ] **Stem helpers in an embedding-free home (Unit 2).** `tokenize`,
      `generic_tokens`, `distinctive_stem`, `ORG_DESCRIPTORS`,
      `DEFAULT_MIN_GENERIC_DF` move from `er_semantic.py` to `resolution.py`;
      `er_semantic.py` re-imports them; behaviour byte-identical (all tests pass
      unchanged); the leak-guard still green (`resolution.py` imports nothing
      banned).
- [ ] **Stem-gated `resolve_entities` (Unit 3).** A difflib merge at/above 0.85 is
      asserted only when the names share a distinctive token (typo-tolerant); the
      assertion `reason` names the shared token so it stays inspectable. The cohort
      `Granite/Pyrite/Cobalt/Basalt Logistik GmbH` resolves to **four** clusters.
      **ADR 0018** records the design + the intentional core-touch.
- [ ] **No regression, measured (Unit 3).** All three batteries
      (business/devex/github_actions) read byte-identical to M7
      (`eval/history.jsonl` numbers reproduced; faithfulness 1.0); the
      business/devex graph proof tests (Bayerische, Müller, catalog↔on-call) still
      pass.
- [ ] **Specimens rewritten + new edge planted (Unit 3).**
      `test_scale::test_generic_suffix_firms_over_merge_at_the_threshold` flips to
      assert the cure; `test_er_metrics` precision/recall updated (difflib
      0.50→1.00, union 0.67→1.00, the "residual is entirely difflib" test becomes
      "no residual over-merge"); a **new** `test_scale` specimen asserts the
      character-identical distinct-firm over-merge that stem-gating cannot fix, with
      multi-field ER named as the next lever.
- [ ] **Close (Unit 4).** Gate green under multiple `PYTHONHASHSEED` values;
      WRITEUP "deterministic ER precision" section (before/after, the new edge);
      README + CHANGELOG `[milestone-8]`; STATUS; the ADR 0008 empty-diff core check
      run and the **intentional** exception documented; tag `milestone-8`; memory;
      next-milestone kickoff handed back.

## Scope

**In — the unit breakdown (one PR each, spec each):**

| Unit | Spec | Content |
|---|---|---|
| 1 | 0068 | this plan + the two recorded scope decisions (asked 2026-06-28) |
| 2 | 0069 | lift the deterministic stem helpers from `er_semantic.py` into `resolution.py` (embedding-free home); `er_semantic` re-imports; byte-identical; leak-guard green |
| 3 | 0070 | stem-gate `resolve_entities` (share-a-distinctive-token, typo-tolerant); **ADR 0018**; cure the over-merge; rewrite `test_scale`/`test_er_metrics` specimens; plant the new harder edge; re-measure ER precision/recall; all three batteries byte-identical |
| 4 | 0071 | close: WRITEUP/README/CHANGELOG/STATUS, empty-diff core check + documented exception, tag `milestone-8`, memory, kickoff |

**Out (explicitly):**

- **Multi-field ER (name + address/keys).** The maintainer chose the stem-gate
  lever, not multi-field (ADR 0004 future work). It is named as the next lever for
  the new recorded edge (distinct firms with character-identical names), not built
  here.
- **Embeddings / the M7 regime.** `er_semantic.py` and `TESSERA_EMBEDDINGS` are
  unchanged; M8 is purely the deterministic offline pass. No cloud, no online run.
- **Embeddings on the claim / faithfulness path.** `is_supported` stays
  deterministic and structural; ADR 0005 stays deferred.
- **A new gated eval metric for ER.** Faithfulness remains the single hard CI floor;
  ER precision/recall stays a reported measurement (`test_er_metrics`), not a gate.
- A **second real connector**; **agentic/MCP** mode; HANA graph persistence; BTP
  serving. These remain the WRITEUP's named future work.

## Eval impact

- **ER precision up (offline, CI-reproducible):** difflib 0.50→1.00, union
  0.67→1.00 on the labelled pair set; `test_scale` over-merge specimen cured. This
  is the headline and it lands in CI, not as a timestamped online point.
- **Coverage / quality / faithfulness unchanged on every battery.** The cure removes
  over-merges that do not occur in the real demo graphs, so the three batteries read
  byte-identical to M7. This is **asserted by measurement**, not assumed — if a real
  merge were lost, a battery number would move and Unit 3 would catch it.
- **Faithfulness pinned at 1.0.** Re-clustering flows through the business verifier
  shapes (`business/claims.py`); the cure only *splits* spurious clusters, so any
  superlative/compare recomputation stays supported.

## Risks / open questions

- **The holistic-stem trap (the central technical risk).** "Stem-gate the difflib
  pass" naively reads as `similarity(stem_a, stem_b) >= t`, which **breaks
  `search-servce`** (typo in a generic token leaks into the stem). The design answer
  is the **existential shared-distinctive-token** gate, typo-tolerant — it preserves
  every real merge and removes only the generic-suffix collisions. ADR 0018 must make
  this crisp, with the worked table.
- **Losing a correct merge (the regression risk).** A conjunctive gate can only
  remove merges. The only correct merge it could drop is one whose two names share
  **no** distinctive token even typo-tolerantly — which means the firm is named with
  entirely different distinctive words in two records (an acronym-vs-full-name case),
  and difflib would not have reached 0.85 on such a pair anyway. Mitigation: Unit 3
  **measures** all three batteries + the business/devex proof tests; nothing is
  assumed.
- **Corpus-dependence of genericness.** `generic_tokens` uses corpus document
  frequency, so the merge decision now depends mildly on what else is in the graph
  (`Logistik` is generic only at ≥ cutoff occurrences). This is the same property the
  M7 stem mechanism already has; it is documented as a tunable knob, not a solved
  problem. The static descriptor + legal-form stoplist still strips `gmbh`/`service`
  regardless of corpus.
- **Touching the frozen core (the generality decision).** Curing the over-merge
  *properly* means changing `resolve_entities`, ending the empty-diff-core streak
  intentionally. Defensible (a general precision improvement belongs in core, not a
  vertical) and recorded in **ADR 0018**, refining ADR 0004's matching method. The
  leak-guard is protected by keeping the stem helpers in the embedding-free
  `resolution.py`. The M8 empty-diff check documents this as the one sanctioned core
  delta, naming exactly the changed lines.
- **Leak-guard breach risk.** The stem helpers must land in `resolution.py` (stdlib-
  only), not stay imported from `er_semantic.py` (banned), or `graph.py` importing
  them would pull an embedding import into the verifier's closure. Unit 2 does the
  move first, with the leak-guard green, precisely to de-risk Unit 3.
