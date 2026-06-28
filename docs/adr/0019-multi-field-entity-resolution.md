# 0019. Multi-field entity resolution: a two-way address gate

- **Status:** accepted
- **Date:** 2026-06-28

## Context

Name-only entity resolution (ADR 0004), even with Milestone 8's stem gate
(ADR 0018), has a floor that name evidence cannot cross. Milestone 8 recorded three
residuals, each pinned by a test, all naming the **same** next lever — multi-field
ER (name + address), which ADR 0004 had already called out as *"an additive
extension — more signals into the same assertion layer — not a redesign"* because
address nodes already exist in the graph as the targets of `has_address` edges:

1. **Character-identical distinct firms** — two genuinely different firms carry the
   *same* name; only a different address tells them apart. They over-merge.
2. **Two-firm generic-suffix collision** — a suffix is recognised as generic only
   once it spans `min_df` (= 3) distinct firms; two firms sharing a suffix are below
   that floor and over-merge.
3. **Double-typo pair** — a genuine same-firm pair whose distinctive tokens are
   *both* typo'd (no shared token, stems > `max_stem_edits` apart) is vetoed by the
   stem gate; on the demo data it survives only by transitive bridging.

Residuals 1 and 2 are **over-merges** (a precision defect — the firms differ, so a
disagreeing address must *split* them); residual 3 is an **under-merge** (a recall
defect — the firms are the same, so an agreeing address must *bridge* them). The
maintainer authorised acting on this (the Milestone-9 scope questions, answered
2026-06-28): match on **name + address**, combine via a **two-way deterministic
gate**, and add a synthetic same-name/different-address pair to make the close a
measured before/after.

Two constraints shape the design. First, resolved entities are **connected
components** over additive `Resolution` assertions (ADR 0004): a merge either exists
or it does not, so a confidence number can *not* change cluster membership — only a
gate (assert-or-veto) can actually split an over-merge or bridge an under-merge.
Second, the faithfulness verifier must stay **embedding-free** (the standing
leak-guard, `tests/test_semantic.py`): the address comparison must be pure-stdlib
string work in `resolution.py`, which is already in the verifier's import closure.

## Decision

`KnowledgeGraph.resolve_entities` gains an **optional, ordered**
`match_fields: Sequence[str] = ()` — attribute keys (beyond the name) to compare as a
corroborating identity signal. The source attaches those fields as node
`attributes` (the existing mechanism); the engine stays general — it compares
whatever fields it is told to, knowing nothing about "addresses" (the ADR 0011
ownership pattern; the schema knowledge of *which* attributes are an address lives
in `sources/salt.py`). The default `()` is **byte-identical** to Milestone 8 (the
devex / github_actions none-path).

**The address signal** (`resolution.compare_match_fields`, pure-stdlib) is one of
three verdicts for a candidate pair, computed over the ordered `match_fields`:

- `match_fields` are **ordered by decisiveness** — the first field present
  (non-empty) on *both* nodes decides, so a clean key (postal code) is never
  overridden by a noisy secondary field (city).
- **AGREE** — that field's normalized `similarity` is `>= DEFAULT_FIELD_MATCH_THRESHOLD`
  (0.9, high by design so a postal code must be near-identical).
- **CONTRADICT** — that field is present on both but below the threshold.
- **NEUTRAL** — no field is present on both. **Absence is never a contradiction**, so
  a node lacking an address falls back to the name-only decision.

**The two-way gate** folds the signal into the existing name decision. It is reached
only for pairs the name pass already accepts (`similarity(a, b) >= threshold`):

| name pass (M8 stem gate) | address signal | outcome |
|---|---|---|
| confirmed | CONTRADICT | **veto** — same name, different address → distinct firms (residuals 1 & 2) |
| confirmed | AGREE / NEUTRAL | merge (as M8; the reason notes any agreement) |
| vetoed (stem gate) | AGREE | **merge** — address bridges a name-vetoed near-match (residual 3) |
| vetoed (stem gate) | CONTRADICT / NEUTRAL | veto (as M8) |

- **The corroboration arm is bounded — and its residual precision risk is a measured
  edge, not a code guarantee.** It is reached only when the *name* similarity already
  cleared the threshold (the loop skips lower pairs), so "two different firms in the
  same building" with *dissimilar* names can never false-merge on address agreement
  alone. The narrow case it *can* in principle reach is two genuinely distinct firms
  that are name-similar (`>= threshold`) but stem-vetoed (distinctive heads both typo'd
  or sharing only a generic suffix) **and** that share an *exact* address — a same-
  building, similar-name coincidence. The exact-equality field match (below) removes
  the *accidental* version of this (a different postal can no longer coincidentally
  agree), leaving only genuine same-address pairs; on the synthetic data none exists
  (distinct firms have distinct postals), so the arm adds no false merge there
  (measured). This is the symmetric counterpart of the veto arm's postal-anchored
  limitation — a recorded measured edge whose next lever is a registration/tax key,
  not a logic error.
- **Field agreement is exact normalized equality, not a fuzzy ratio.** The review of
  this unit caught that a difflib character ratio calls genuinely different postal
  codes near-identical (`"D-20095"` ~ `"20095"` = 0.909, `"20095"` ~ `"200950"` =
  0.909), which would have broken the veto arm. `DEFAULT_FIELD_MATCH_THRESHOLD = 1.0`:
  a field agrees only when its `normalize`d values are equal. `normalize` folds
  umlauts/diacritics, so a city's legitimate spelling variants still agree, while a
  postal code (an identity key) must match exactly. A genuinely fuzzy field (street,
  with abbreviation variants) would take a threshold `< 1.0`; none is wired (postal +
  city carry the signal).
- **The additive/reversible model is unchanged (ADR 0004).** A confirmed pair is
  still an ordinary `Resolution` with a `reason` (now naming the deciding address
  field) and `confidence`; clusters stay derived connected components;
  `remove_resolution` re-splits.
- **Confidence stays the name-similarity proxy, stated honestly.** The multi-field
  evidence is recorded in the assertion `reason` (which field agreed/contradicted),
  **not** as a recalibrated confidence number — ADR 0004's standing honesty that
  `confidence` is a proxy, not a calibrated probability, would be violated by
  fabricating a combined score. Reflecting agreement in the *reason* (and in whether
  the merge exists at all) is the honest reflection.

**Postal code is the stable anchor.** In the synthetic SALT corpus, distinct firms
have distinct postal codes and every duplicate of one firm shares the canonical
postal (only street/city *spelling* is varied), so a postal-anchored comparison
separates the residuals from genuine merges with no false split on the existing
data. City is a secondary field (umlaut/diacritic folding makes it match exactly);
street is left out as a decisive key (abbreviation variants make it noisy).

**This is the second intentional change to the frozen core** (ADR 0008's empty-diff
list) since the verticals were built — the first was Milestone 8's stem gate. It is
justified on the same grounds: a *general* ER capability belongs in the
vertical-neutral engine, not a vertical (the schema knowledge stays in the source).
The empty-diff check at the milestone close documents `resolve_entities` +
`resolution.py` as the one sanctioned core delta.

## Consequences

- **Easier:** the three name-only residuals are resolvable by a second signal,
  deterministically and *in CI* — character-identical firms with different addresses
  split, two-firm suffix collisions split, and a double-typo pair with the same
  address merges directly (no longer reliant on transitive bridging). No online run,
  unlike M6/M7.
- **Non-regression, measured.** The gate is inert on the *existing* demo data (every
  genuine merge has an agreeing postal; no character-identical distinct firm exists
  yet), so the business and devex **resolved cluster signatures stay byte-identical**
  (Unit 3 pins this, hashed, not assumed) and all three batteries read byte-identical.
  The corroboration arm may *add* a resolution edge on the demo graph (the Noridc/
  Nordic Timbre double-typo pair now merges directly) — the cluster is unchanged
  (already connected by transitivity), so the signature is identical while the
  assertion set is strictly more robust.
- **Accepted cost — postal-anchored, not postal-perfect.** The veto arm splits a
  genuine same-firm pair if its two records carry *different* postal codes (real-world
  data entry). On the synthetic data this never happens (postal is the fixed canonical
  value); on real SALT it could, and is the honest limitation. The fallback is
  NEUTRAL when a postal is absent — absence is never read as contradiction.
- **Accepted cost — corroboration is bounded to name-similar pairs.** A genuine pair
  whose names diverge *below* the name threshold but share an address is not bridged
  (the loop never reaches it). Widening the corroboration band is named future tuning,
  not built here, to keep the recall arm provably safe.
- **Faithfulness stays the single hard gate, structural and embedding-free.** The
  gate only splits/bridges clusters, so every business superlative/compare claim the
  verifier recomputes over `clusters()` stays supported; the leak-guard holds
  (`compare_match_fields` is pure-stdlib in `resolution.py`).
- ADR 0004's "single name-similarity threshold … transitive over-merge" cost is
  **narrowed further**: M8 closed the generic-suffix case; M9 closes the
  character-identical and two-firm-suffix cases with the address signal. The residual
  is now only the genuinely address-ambiguous case (same name *and* same address but
  distinct firms — which a registration/tax key, named future work, would separate).

## Alternatives considered

- **Confidence modulator only** (address raises/lowers `Resolution.confidence`,
  cluster membership unchanged). **Rejected** — resolved entities are connected
  components, which do not consult confidence, so a modulator resolves *none* of the
  three residuals: the over-merges still merge (just with lower confidence) and the
  under-merge still splits. Honest about the evidence, but it does not do the job. A
  gate is required.
- **Hard gate on address alone, ignoring the name decision.** Rejected: two distinct
  firms can share an address (a serviced office); address agreement is corroborating,
  not sufficient. The gate must be *conjunctive* with a name signal — which the
  bound to `similarity >= threshold` provides.
- **A registration/tax key as the disambiguator now.** The cleanest exact key, and a
  real SALT field, but it requires inventing a new synthetic column and an exact-match
  comparison is algorithmically trivial. The maintainer chose name + address (already
  in the graph, fuzzy, more realistic); a key is named as a possible later field for
  the residual same-name/same-address case.
- **Comparing all `match_fields` conjunctively** (agree only if *every* present field
  agrees; contradict if *any* disagrees). Rejected in favour of first-present-decides:
  a noisy secondary field (a street abbreviation variant) would otherwise flip a clean
  postal-code agreement to CONTRADICT and wrongly split a genuine merge. Ordering by
  decisiveness lets the stable key carry the verdict.
- **Street-level fuzzy matching as a decisive key.** Rejected: street carries
  abbreviation variants (`Industriestrasse`/`Industriestr.`) that make it a noisy
  signal; postal + city carry the verdict cleanly. Street stays available in the data,
  named as a future secondary field.
- **Putting the address comparison in the vertical** (like M7's embedding ER regime,
  `er_semantic.py`). Rejected: M7 stayed vertical-side because embeddings would breach
  the leak-guard. Address comparison is pure-stdlib and a *general* ER capability, so
  it belongs in the core (the same reasoning as ADR 0018's stem gate). The schema
  knowledge of which attributes are an address stays in the source.
