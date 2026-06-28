# 0070. Stem-gate resolve_entities: cure the generic-suffix over-merge

- **Phase / milestone:** Milestone 8, Unit 3 (the substantive unit)
- **Issue:** —
- **Status:** implemented (autonomous mode, per spec 0018)

## Problem

The deterministic ER pass `KnowledgeGraph.resolve_entities` asserts a merge on raw
`difflib` full-name similarity ≥ 0.85. A long shared *generic* suffix dominates the
ratio, so distinct firms collapse (`Granite/Pyrite/Cobalt/Basalt Logistik GmbH`,
measured in `tests/test_scale.py`). Milestone 7's additive embedding regime could
not remove this difflib false positive (the recorded residual: difflib precision
0.50, union 0.67 in `tests/test_er_metrics.py`). The recorded next lever — chosen by
the maintainer for Milestone 8 — is to **stem-gate the difflib pass itself**: a
deterministic, offline, CI-reproducible change to the engine core.

## Acceptance criteria

- [x] `resolve_entities` confirms a character match only when the names share a
      distinctive (non-generic) signal; the generic-suffix cohort
      (`Granite/Pyrite/Cobalt/Basalt Logistik GmbH`) resolves to **four** clusters.
- [x] **No resolved cluster changed, measured.** The business and devex **cluster
      signatures are byte-identical** before and after (verified by hashing
      `clusters()` on both graphs against pre-gate `main`); all three eval batteries
      reproduce M7 numbers exactly; the demo-graph proof tests (Bayerische 4-way,
      Müller, Nordic Timber, catalog↔on-call variants) still pass. (The gate is a
      pure pairwise veto; it *can* drop a correct pairwise edge for a double-typo
      head — the real `Noridc Timber`/`Nordic Timbre` edge at 0.857 — but that firm's
      cluster is preserved by transitive bridging, so the resolved entities are
      unchanged; recorded as a residual, not claimed away.)
- [x] `tests/test_er_metrics.py` updated: gated difflib precision 0.50 → **1.00**,
      union 0.67 → **1.00**, recall unchanged at 0.50 (the abbreviation/synonym
      misses remain the embedding's job); the "residual is entirely difflib" test
      becomes "the over-merge is cured."
- [x] `tests/test_scale.py` over-merge specimen flips to assert the cure; a **new**
      specimen pins the residual the gate cannot reach (character-identical distinct
      firms) with multi-field ER named as its next lever.
- [x] Faithfulness gated at 1.0 throughout; the leak-guard stays green (the gate is
      embedding-free, in `resolution.py`).
- [x] Deterministic across `PYTHONHASHSEED` values (cluster signature stable).
- [x] **ADR 0018** records the design, the intentional core-touch, and the rejected
      alternatives (holistic stem similarity, per-pair only, naive corpus DF).

## Scope

**In:** `resolution.confirm_name_match` + `resolution.corpus_generic_tokens` (the
gate + its corpus-derived stoplist); `resolve_entities` calls them; the assertion
`reason` now names the shared distinctive token / stem. Specimen rewrites in
`test_scale` and `test_er_metrics`; ADR 0018; ADR nav/index entries.

**Out:** multi-field ER (the residual's next lever, ADR 0004 future work, not built);
the M7 embedding regime (`er_semantic.py` unchanged); any change to `eval/metrics.py`
or the faithfulness definition; any online/cloud run (this unit is fully offline).

## The design (recorded in full in ADR 0018)

A merge at char-similarity ≥ 0.85 is **confirmed** only when the names share a
distinctive signal:

1. **Corpus genericness** (`corpus_generic_tokens`): a token is generic iff ≥ `min_df`
   of the names containing it stay mutually dissimilar **once that token and the
   already-known generics are removed** (iterated to a fixpoint, so a multi-token
   suffix like `Trade Logistik GmbH` is fully recognised). This strips `logistik`
   (cross-firm) but keeps `bayerische` (repeated across one firm's duplicate
   records), avoiding the naive-document-frequency trap. Single-character tokens
   (`G.m.b.H` → `g m b h`) are dropped so a punctuated legal form never pollutes a
   stem.
2. **Confirm** on a shared distinctive token (the identity head, robust to a typo
   elsewhere), or a near-identical distinctive stem, or a small character edit
   distance (so a single typo in a short head survives the suffix being stripped), or
   two entirely-generic names; else **veto**.

Conjunctive tightening: the gate only ever *removes* a pairwise merge the bare ratio
would have made, never adds one. The merges it removes are usually generic-suffix
over-merges; it can also drop a genuine double-typo edge (rescued by transitivity on
the demo data — the resolved cluster signatures are byte-identical, but that is a
corpus property, not a guarantee). Three residuals are recorded and pinned by tests:
character-identical distinct firms, two-firm (`< min_df`) suffix collisions, and the
double-typo-with-no-bridge recall risk — all pointing at multi-field ER.

## Eval impact

- **ER precision up, offline/CI-reproducible:** difflib 0.50 → 1.00, union 0.67 →
  1.00 on the labelled pair set; the `test_scale` over-merge specimen cured.
- **All three batteries byte-identical to M7** (faithfulness 1.0; devex 0.950/0.889,
  github_actions 0.833/0.800 offline misses unchanged) — the over-merges the cure
  removes are absent from the real graphs, and the one real edge it drops is
  transitively bridged, so resolved clusters are unchanged.

## Risks / open questions

- **Losing a correct merge** — guarded by the cluster-signature equality check (not
  assumed) and by pinned regression specimens. The design was hardened *after*
  measurement and an adversarial review: a naive per-pair gate vetoed real merges
  (`Maple eLaf`/`Maple Leaf`); a single-pass genericness left multi-token suffixes
  uncured; and a short-head typo under a generic suffix (`Stein`/`Stien`) was wrongly
  vetoed until the edit-distance fallback and single-character-token filter were
  added. Each is now a pinned test (`tests/test_resolution.py`).
- **The cure needs ≥ `min_df` firms** to recognise a suffix as generic; a two-firm
  generic-suffix collision folds into the recorded residual (multi-field ER). A
  tunable knob, documented in ADR 0018.
- **First intentional core change** since the verticals (ADR 0008 empty-diff). A
  *general* precision improvement legitimately belongs in core; documented as the one
  sanctioned delta at the milestone close.
