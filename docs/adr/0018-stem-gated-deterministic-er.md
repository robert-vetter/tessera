# 0018. Stem-gated deterministic entity resolution: cure the generic-suffix over-merge

- **Status:** accepted
- **Date:** 2026-06-28

## Context

The deterministic ER pass (`KnowledgeGraph.resolve_entities`, ADR 0004) asserts a
merge whenever `difflib.SequenceMatcher` over the two **full normalized names**
clears `DEFAULT_RESOLUTION_THRESHOLD = 0.85`. When the part two names share is a
long *generic* suffix, that suffix dominates the character ratio and distinct firms
collapse — measured in `tests/test_scale.py`:

- `Granite Logistik GmbH` ~ `Pyrite Logistik GmbH` = 0.865 → over-merge
- `Cobalt Logistik GmbH` ~ `Basalt Logistik GmbH` = 0.889 → over-merge

Milestone 7 added an **additive** embedding regime (ADR 0016) that closed the
`checkout-svc` recall miss, but — being additive — it could not *remove* a difflib
false positive. The residual was recorded honestly (`tests/test_er_metrics.py`:
difflib precision 0.50, union 0.67) with the named next lever: *"apply the same
stem-gating to the difflib pass … or multi-field ER."* The maintainer authorized
acting on it (the Milestone-8 scope questions, answered 2026-06-28): **stem-gate the
difflib pass only** (not multi-field ER), and **keep a new measured edge** rather
than claim the over-merge universally solved.

This is the inverse of ADR 0016: M7 *added* merges (recall) on the embedding path;
M8 *removes* over-merges (precision) on the deterministic path — and unlike M6/M7,
entirely **offline and CI-reproducible** (no embedding, no cloud, no online run).

## Decision

**A character-similarity match is confirmed only when the two names share a
distinctive (non-generic) signal** — a conjunctive *tightening* of the existing
pass, in the engine core (`resolution.confirm_name_match`, called from
`resolve_entities`). It can only ever *remove* a merge the bare ratio would have
made, never add one.

- **Genericness is corpus-derived, not per-pair and not raw document frequency**
  (`resolution.corpus_generic_tokens`). A token is generic when it spans **≥ `min_df`
  distinct firms**: `≥ min_df` of the names containing it stay mutually dissimilar
  *once that token and all tokens already known to be generic are removed from
  each*. Removing the token first is the crux — it breaks the circularity a shared
  generic suffix creates (`Granite/Pyrite/Cobalt Logistik GmbH` are pairwise ≥ 0.85
  *because of* `logistik`, so a naive document-frequency count cannot see `logistik`
  as cross-firm). The derivation is **iterated to a fixpoint** so a *multi-token*
  generic suffix is handled: removing `logistik` from `Granite Trade Logistik GmbH`
  leaves `trade` propping similarity, but re-scanning with `logistik` already
  stripped exposes the heads and flags `trade` too. Static generics (org descriptors
  ∪ legal forms) seed the set; the traversal is over a canonicalised, sorted name
  list, so the result is independent of ingestion order. **Single-character tokens
  are dropped** before any of this — a punctuated legal form (`G.m.b.H` → `g m b h`,
  `A/S` → `a s`) abbreviates into single letters that carry no identity but would
  otherwise pollute a distinctive stem.
- **Confirm on a shared distinctive token, a near-identical distinctive stem, or a
  small edit distance.** If the names share any non-generic token (the firm's
  identity head — `maple`/`timber`/`schaefer`), they co-refer — robust to a typo or
  abbreviation elsewhere. Otherwise compare the distinctive stems (names minus
  generic tokens) as whole strings at a named threshold
  (`DEFAULT_DISTINCTIVE_STEM_THRESHOLD = 0.85`) **OR within a small character edit
  distance** (`DEFAULT_MAX_STEM_EDITS = 2`). The edit-distance fallback is load-
  bearing: stripping a shared generic suffix *amplifies* a one-character typo in a
  short head (`stein`~`stien` is ratio 0.800 but 2 edits), so the ratio alone would
  wrongly veto a real typo variant; two genuinely different heads still veto
  (`granite`~`pyrite` = 4 edits, `cobalt`~`basalt` = 3). Two **entirely generic**
  names confirm (the match rests on identical generic forms — e.g. `"Service GmbH"`
  twice), never silently dropped.
- **Embedding-free, so the leak-guard is untouched.** The gate is pure-stdlib
  deterministic string work in `resolution.py` — already in the verifier's import
  closure and banned from importing any vector/provider module. The distinctive-stem
  primitives were relocated from `er_semantic.py` (banned) to `resolution.py`
  precisely so the core could share them without pulling an embedding import toward
  `eval/metrics.py` (the standing leak-guard, `tests/test_semantic.py`).
- **Additive/reversible model unchanged (ADR 0004).** A confirmed match is still an
  ordinary `Resolution` with a `reason` (now also naming the shared distinctive
  token / stem) and `confidence` = score; clusters stay derived connected
  components; `remove_resolution` re-splits.

**This is the first intentional change to the frozen core** (ADR 0008's empty-diff
list) since the verticals were built. It is justified: a *general* ER precision
improvement belongs in the vertical-neutral engine, not a vertical (the opposite of
ADR 0016's embedding regime, which stayed vertical-side for leak-guard reasons). The
empty-diff check at the milestone close documents this as the one sanctioned core
delta, naming the changed functions.

**Keep the measured edges.** Stem-gating cures the generic-suffix collision
(single- and multi-token suffixes, for cohorts ≥ `min_df`), but not name-only ER's
floor. Three residuals are recorded and pinned by tests
(`tests/test_scale.py`/`tests/test_resolution.py`), in the Milestone-5
keep-a-measured-edge discipline, all pointing at multi-field ER (name + address,
ADR 0004 future work) as the next lever:

1. **Character-identical distinct firms** — same distinctive name, only an address
   or registration number tells them apart; they still over-merge.
2. **Two-firm generic-suffix collision** — a suffix is recognised as generic only
   once it spans `min_df` (= 3) distinct firms; two firms sharing a suffix are below
   that floor (frequency cannot distinguish them from a two-firm typo pair) and over-
   merge.
3. **Double-typo recall risk** — a genuine match whose distinctive tokens are *both*
   typo'd (no shared token, stems > `DEFAULT_MAX_STEM_EDITS` apart) is vetoed; on the
   demo data it survives by transitive bridging, but a short-headed double-typo pair
   with no cleaner co-referent would lose its cluster.

## Consequences

- **Easier:** the generic-suffix over-merge is cured deterministically and
  *in CI* — difflib precision 0.50 → 1.00, union 0.67 → 1.00 on the labelled pair
  set (`tests/test_er_metrics.py`); the `test_scale` specimen flips from asserting
  the over-merge to asserting four distinct firms. No online run, unlike M6/M7.
- **Non-regression, measured and honestly scoped.** All three eval batteries read
  byte-identical to M7 (faithfulness 1.0; devex 0.950/0.889 and github_actions
  0.833/0.800 offline misses unchanged), and the business/devex **resolved cluster
  signatures are byte-identical** before and after (measured, not assumed). What the
  gate removes is *usually* a generic-suffix over-merge — but it is a pure pairwise
  veto, and it **can** drop a genuine match whose distinctive tokens are *both* typo'd
  at once (no shared token, stems > 2 edits apart): the real `Noridc Timber A/S` ~
  `Nordic Timbre AS` edge (0.857) is vetoed. The clusters stay identical only because
  that firm's other variants bridge it transitively through a cleaner co-referent —
  a property of *this* corpus, not a general guarantee. The corpus-derived genericness
  is what keeps the common case safe: a naive document-frequency stoplist would
  mis-strip a distinctive token that repeats across one firm's duplicate records
  (`Bayerische` ×4) and split a genuine cluster — the trap the remove-then-compare,
  single-removal-fixpoint definition avoids.
- **Accepted cost — the cure needs ≥ `min_df` firms to recognise a suffix as
  generic.** A two-firm generic-suffix collision (only `Granite` and `Pyrite`, no
  `Cobalt`/`Basalt`) is indistinguishable by frequency from a two-firm typo pair and
  would not be cured — folded into the recorded residual (multi-field ER is the
  lever). Documented as a tunable knob (`min_df`, the stem threshold), not a solved
  problem.
- **Accepted cost — corpus-dependence.** A merge decision now depends mildly on what
  else is in the graph (whether a token reaches the cross-firm cutoff). This is the
  same property the M7 stem mechanism already had; the static descriptor + legal-form
  stoplist still applies regardless of corpus.
- **Faithfulness stays the single hard gate, structural and embedding-free.** The
  gate only *splits* spurious clusters, so any business superlative/compare claim the
  verifier recomputes over `clusters()` stays supported; the floor is unaffected.
- ADR 0004's "single name-similarity threshold … transitive over-merge" cost is
  **narrowed**: the generic-suffix case is closed; the residual is the
  character-identical-name case, which name-only ER cannot reach by construction.

## Alternatives considered

- **Holistic distinctive-stem similarity** (`similarity(stem_a, stem_b) >= t`).
  Rejected: it breaks the correct `search-service` ↔ `search-servce` typo merge —
  the typo `servce` is not a recognised generic, so the stems become `"search"` vs
  `"search servce"` (~0.67) and the merge is wrongly vetoed. The existential
  shared-token rule (plus stem similarity as a fallback) is robust to typos in
  generic tokens.
- **Per-pair shared-token removal only** (drop the exactly-shared tokens, compare
  residuals). Rejected after measurement: it vetoes many real demo-graph merges
  (`Maple eLaf`/`Maple Leaf`, `Nordic`/`Noridc`, `Schäfer`/`Schaefer`) whose
  difference concentrates in one typo'd token, because a single short residual pair
  (`elaf`~`leaf` = 0.5) cannot carry the match. Corpus genericness that keeps the
  shared distinctive context is required.
- **Naive corpus document frequency** (token generic iff it appears in ≥ `min_df`
  names). Rejected: it marks a distinctive token generic when it repeats across one
  firm's duplicate records (`Bayerische` ×4 → DF ≥ 3 → stripped → the cluster
  splits). The remove-the-token-then-judge-similarity definition distinguishes
  duplicate records (still similar with the token gone) from cross-firm boilerplate
  (dissimilar with it gone).
- **Lower / raise the global `difflib` threshold.** Rejected (as in ADR 0010/0016):
  the over-merges (0.865, 0.889) and the correct typo merges (`Schäfer` 0.868,
  `Nordwind Log` 0.857) occupy the *same* similarity band, so no single threshold
  separates them. The problem is which tokens carry the similarity, not how high it
  is.
- **Multi-field ER (name + address/keys) now.** The stronger precision lever and
  ADR 0004 future work, but a larger change; the maintainer chose the stem-gate lever
  for this milestone. Kept on record as the next lever for the recorded
  character-identical-name residual.
- **An embedding signal inside `resolve_entities`.** Rejected (as in ADR 0016): it
  would pull an embedding import toward the verifier's closure and risk the
  leak-guard. The cure here is deterministic and embedding-free by construction.
