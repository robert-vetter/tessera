# 0072. Milestone 9 plan: multi-field entity resolution (name + address)

- **Phase / milestone:** Milestone 9 — Multi-field entity resolution: resolve the
  three Milestone-8 residuals with a second deterministic signal (address)
  (post-roadmap; ROADMAP phases complete and tagged `phase-0`…`phase-4`; hardening
  `milestone-5`; embeddings-on-SAP `milestone-6`; embeddings-beyond-retrieval
  `milestone-7`; deterministic-ER-precision `milestone-8`)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018: decisions recorded here
  instead of asked — except the three project-shaping scope questions below, which
  were asked and answered 2026-06-28)

## Problem

Milestone 8 cured the *generic-suffix* over-merge by stem-gating the deterministic
`difflib` pass (ADR 0018) — a precision win, in the core, provable in CI. But it
also recorded, and pinned by tests, three residuals that **name-only ER cannot
reach by construction**:

1. **Character-identical distinct firms** (`tests/test_scale.py::
   test_character_identical_distinct_firms_still_over_merge`) — two genuinely
   different firms carrying the *same* name (only a different address / registration
   tells them apart) still over-merge. This is name-only ER's floor.
2. **Two-firm generic-suffix collision** (`…::
   test_two_firm_generic_suffix_is_a_recorded_residual`) — a suffix is recognised as
   generic only once it spans `min_df` (= 3) distinct firms; two firms sharing a
   suffix are below that floor and over-merge (frequency cannot tell them from a
   two-firm typo pair).
3. **Double-typo recall risk** (ADR 0018 residual 3) — a genuine match whose
   distinctive tokens are *both* typo'd (no shared token, stems > `max_stem_edits`
   apart) is vetoed by the stem gate; on the demo data it survives only by transitive
   bridging through a cleaner co-referent.

All three name the **same** next lever, recorded across ADR 0004's "future work"
(*"name-only matching is a deliberate slice simplification; real master-data ER
matches on multiple fields … address nodes already exist in the graph … an additive
extension, not a redesign"*) and ADR 0018's residual section: **multi-field ER
(name + address)**. The maintainer authorised acting on it (the Milestone-9 scope
questions, answered 2026-06-28).

Residuals 1 and 2 are **over-merges** (a precision defect — the firms differ, so a
disagreeing address must *split* them); residual 3 is an **under-merge** (a recall
defect — the firms are the same, so an agreeing address must *bridge* them). Closing
all three therefore needs a **two-way** address signal, not a one-directional gate.

Like Milestone 8 — and unlike Milestones 6–7 — this is **deterministic, offline, and
fully CI-reproducible**: no embedding, no cloud, no online run. The claim/faithfulness
path stays embedding-free (address comparison is pure-stdlib string work in the
already-verifier-reachable `resolution.py`; the leak-guard is untouched).

**Maintainer decisions (asked 2026-06-28, because they are project-shaping):**

1. **Match fields — name + address** (not a new registration/tax-key column).
   Address already lives in the graph as `has_address` edges to address nodes that
   carry `PostalCode`/`CityName`/`StreetName`, so this is the true "additive
   extension — more signals into the same assertion layer" ADR 0004 named, with **no
   schema invention**. Postal code is the stable anchor (see the design). A
   registration/tax key (an exact, trivial disambiguator that would require a new
   synthetic column) stays out of scope, named as a possible later field.
2. **Combine rule — a two-way deterministic gate.** Address *disagreement* vetoes a
   name-merge (splits residuals 1 & 2); address *agreement* corroborates a
   name-vetoed near-match (bridges residual 3). The merge `confidence` additionally
   reflects multi-field agreement, for inspection. It must be a **hard gate**, not a
   mere confidence modulator, because resolved entities are *connected components* —
   confidence does not change cluster membership, so only a gate can actually split
   an over-merge or bridge an under-merge. (The rejected "confidence-only" option is
   recorded in ADR 0019.)
3. **Synthetic data — add a same-name / different-address disambiguation pair.**
   Two genuinely distinct firms sharing one name at two different addresses are
   appended to the synthetic SALT corpus (fixed rows, Atlas-style, outside the RNG
   stream so existing rows stay byte-identical), turning the `test_scale` residual
   into a **measured eval before/after** (the Milestone-5/6 "measured miss → measured
   close" discipline): name-only ER wrongly merges-and-answers the ambiguous-name
   question; multi-field ER splits the firms so the answer path correctly **refuses
   as ambiguous**.

## The design (the one technical decision, recorded for ADR 0019)

`KnowledgeGraph.resolve_entities` gains an **optional, ordered `match_fields`**
parameter — attribute keys (beyond the name) to compare as a corroborating identity
signal. Default `()` → name-only → **byte-identical** to Milestone 8 (the devex /
github_actions none-path). The business vertical opts in with
`match_fields=("postal_code", "city_name")`; the source denormalises each customer's
linked address onto the customer node and exposes the same fields on the address
node (schema knowledge stays in `sources/salt.py`, engine stays general — the
ADR 0011 ownership pattern).

For a candidate pair the name pass already evaluates (`similarity(a, b) >=
threshold`), the **address signal** over `match_fields` is one of three values,
computed deterministically in `resolution.py`:

- **CONTRADICT** — the first `match_field` present on *both* nodes disagrees
  (normalised dissimilar). Postal codes are the decisive key: distinct firms have
  distinct postals.
- **AGREE** — the first `match_field` present on both nodes agrees.
- **NEUTRAL** — no `match_field` is present on both (no signal).

`match_fields` are **ordered by decisiveness**: the first field present on both nodes
decides (postal before city), so a noisy secondary field can never override a clean
key. The two-way gate then folds the address signal into the existing name decision:

| name pass (M8 stem gate) | address signal | outcome |
|---|---|---|
| confirmed | CONTRADICT | **veto** (over-merge split — residuals 1 & 2) |
| confirmed | AGREE / NEUTRAL | merge (as M8; reason notes the agreement) |
| vetoed (stem gate) | AGREE | **merge** (address bridges — residual 3) |
| vetoed (stem gate) | CONTRADICT / NEUTRAL | veto (as M8) |

The corroboration arm is **bounded to name-similar pairs** (`similarity >= threshold`
already holds — the loop never reaches a low-name-similarity pair), so "two different
firms in the same building" (low name similarity) can never false-merge on address
agreement alone. The gate stays a pure pairwise decision over the additive,
reversible `Resolution` model (ADR 0004): a confirmed pair is still an ordinary
`Resolution` carrying its reason + confidence; clusters stay derived connected
components; `remove_resolution` re-splits.

**This is the second intentional change to the frozen core** (ADR 0008's empty-diff
list) since the verticals were built — the first since Milestone 8's stem gate. It is
justified on the same grounds: a *general* ER capability belongs in the
vertical-neutral engine, not a vertical (the schema knowledge stays in the source).
ADR 0019 records the design + the intentional core-touch; the empty-diff check at the
milestone close documents it as the one sanctioned core delta.

## Success criterion

The three Milestone-8 residuals are **resolved by a second deterministic signal**,
offline and **provably in CI**, with the headline landing as a measured eval close:

- The `test_scale` residual specimens flip: character-identical firms with different
  addresses now resolve to **two** entities; the two-firm generic-suffix pair with
  different addresses **splits**; the double-typo pair with the same address **merges
  directly** (no longer reliant on transitive bridging).
- **No correct merge is lost and no existing cluster moves.** The multi-field gate
  changes nothing on the *existing* demo data (every genuine merge has an agreeing
  postal; no character-identical distinct firm exists yet) — proven by a
  **cluster-signature byte-identical** hash over the business and devex graphs
  (the Milestone-8 discipline), not assumed.
- **The measured close (the headline).** The appended same-name/different-address
  pair makes the ambiguous-name gold question a **measured miss** under name-only ER
  (it answers, wrongly combining both firms, where a refusal is correct) and a
  **close** under multi-field ER (it refuses as ambiguous). Both points recorded in
  `eval/history.jsonl`; the *after* point is CI-reproducible (unlike the M6/M7 online
  closes).
- **ER precision/recall re-measured** (`tests/test_er_metrics.py`): the
  character-identical-but-different-address pair, formerly name-only ER's unfixable
  floor, is now correctly *not merged* — the residual the M8 docstring named is
  closed by the address signal.
- **Faithfulness stays the single hard gate, structural and embedding-free.** The
  leak-guard holds (address comparison is pure-stdlib in `resolution.py`); the gate
  only splits/bridges clusters, so every business verifier recomputation stays
  supported; the floor stays at 1.0 across all batteries.
- **CI stays offline / deterministic / key-free** — no online run (unlike M6/M7).

## Acceptance criteria

- [ ] **Multi-field engine + ADR 0019 (Unit 2).** `resolve_entities` accepts an
      optional ordered `match_fields`; a `resolution.py` helper computes the
      AGREE / CONTRADICT / NEUTRAL address signal (pure-stdlib, embedding-free); the
      two-way gate vetoes over-merges and bridges corroborated near-matches. Default
      `()` is byte-identical to M8 (none-path). Abstract graph tests pin veto +
      corroborate + none-path; the `test_scale` residual specimens flip; the leak
      guard stays green. **ADR 0019** records the design + the intentional core-touch.
- [ ] **Business wiring, no regression measured (Unit 3).** `sources/salt.py`
      denormalises each customer's address (`postal_code`, `city_name`) onto the
      customer node and exposes the same on the address node; `business/knowledge.py`
      passes `match_fields=("postal_code", "city_name")`. The business and devex
      **resolved cluster signatures are byte-identical** to M8 (hashed, pinned); all
      three batteries read byte-identical (`eval/history.jsonl` numbers reproduced;
      faithfulness 1.0). devex / github_actions untouched.
- [ ] **Synthetic disambiguation pair + the measured close (Unit 4).** Two distinct
      same-named firms at different addresses appended to the generator (fixed rows,
      RNG-stream-safe; existing rows byte-identical; MANIFEST counts updated); a new
      business gold case for the ambiguous-name question (`kind: refuse`); the
      before (name-only, a measured miss) and after (multi-field, refusal restored)
      points recorded in `eval/history.jsonl`; the ER pair set updated (the
      character-identical-different-address pair now correctly not-merged); the
      synthetic case-count pins updated to the new derived count.
- [ ] **Close (Unit 5).** Gate green under multiple `PYTHONHASHSEED` values; WRITEUP
      "multi-field entity resolution" section (the three residuals, the before/after,
      the new boundary); README ER section + numbers; CHANGELOG `[milestone-9]`;
      ADR nav/index; the ADR 0008 empty-diff core check run and the **intentional**
      `resolve_entities`/`resolution.py` delta documented; STATUS; tag `milestone-9`;
      memory; next-milestone kickoff handed back.

## Scope

**In — the unit breakdown (one PR each, spec each):**

| Unit | Spec | Content |
|---|---|---|
| 1 | 0072 | this plan + the three recorded scope decisions (asked 2026-06-28) |
| 2 | 0073 | multi-field engine: optional `match_fields` on `resolve_entities`; the AGREE/CONTRADICT/NEUTRAL address-signal helper in `resolution.py`; the two-way gate (veto + corroborate); none-path byte-identical; flip the `test_scale` residual specimens; **ADR 0019**; pre-merge adversarial multi-agent review |
| 3 | 0074 | wire the business graph (`sources/salt.py` address signatures; `business/knowledge.py` passes `match_fields`); cluster-signature byte-identical pin (business + devex); three batteries byte-identical |
| 4 | 0075 | append the same-name/different-address pair to the synthetic SALT data (RNG-safe, MANIFEST); new ambiguous-name gold case; measure & record the before/after in `eval/history.jsonl`; update the ER pair set + synthetic case-count pins |
| 5 | 0076 | close: WRITEUP/README/CHANGELOG/STATUS, empty-diff core check + documented exception, tag `milestone-9`, memory, kickoff |

**Out (explicitly):**

- **A registration/tax-key field.** The maintainer chose name + address; a new exact
  key column is named as a possible later field, not built here.
- **Embeddings / the M7 regime.** `er_semantic.py` and `TESSERA_EMBEDDINGS` are
  unchanged; the multi-field signal is deterministic and offline. No cloud, no online
  run.
- **Embeddings on the claim / faithfulness path.** `is_supported` stays deterministic
  and structural; ADR 0005 stays deferred.
- **A new gated eval metric for ER.** Faithfulness remains the single hard CI floor;
  ER precision/recall stays a reported measurement (`test_er_metrics`), not a gate.
- **Street-level fuzzy matching as a decisive key.** Street is noisy (abbreviation
  variants); postal + city carry the signal. Street is available in the data and
  named as a future secondary field, not wired decisively.
- A **second real connector**; **agentic/MCP** mode; HANA graph persistence; BTP
  serving. These remain the WRITEUP's named future work.

## Eval impact

- **The measured close (headline, CI-reproducible).** The appended ambiguous-name
  gold case is a **miss under name-only ER** (answers, wrongly combining two firms,
  where a refusal is correct → a quality/coverage drop, faithfulness still 1.0) and a
  **close under multi-field ER** (refuses as ambiguous → back to 1.0). Both points in
  `eval/history.jsonl`; the after is reproducible in CI, not a timestamped online
  point.
- **ER precision up on the labelled set:** the character-identical-but-different-
  address pair, formerly the recorded floor, is correctly not-merged.
- **No existing number moves on the existing data.** The multi-field gate is inert on
  the current demo graph (all genuine merges agree on postal); the business/devex
  cluster signatures are byte-identical, *asserted by measurement*. Any number that
  moved without the new data would be a regression Unit 3 must catch.
- **Faithfulness pinned at 1.0.** Splitting an over-merge and bridging a corroborated
  match both keep every verifier recomputation sound; the floor is unaffected.

## Risks / open questions

- **Perturbing an existing cluster via the new data (the central regression risk).**
  Appending two same-named firms could, in principle, shift `corpus_generic_tokens`
  (e.g. make `trading` generic) and move an existing cluster. Analysis says no — the
  remove-then-count-*distinct-firms* definition (ADR 0018) sees the two Hanseatic
  records as one distinct firm, so `trading` spans {atlas, hanseatic} = 2 < `min_df`
  and stays distinctive. **This must be proven, not assumed:** Unit 3 pins a
  cluster-signature byte-identical hash, and Unit 4 re-checks it after the data lands.
- **Corroboration adding a wrong merge (the recall-arm risk).** The address-agreement
  arm *adds* merges in-core (new vs M8's pure tightening). It is bounded to
  name-similar pairs (`similarity >= threshold`), so the only distinct firms it could
  reach are generic-suffix collisions — which have *different* postals, so the
  address signal is CONTRADICT, not AGREE. Unit 2 measures this on the labelled pair
  set and the abstract graphs; nothing is assumed.
- **Vetoing a correct merge (the precision-arm risk).** The address-disagreement arm
  could split a genuine same-firm pair whose two records carry different postals
  (real-world data entry). On the synthetic data this never happens (postal is the
  fixed canonical value, never varied); on real SALT it could, and is documented as
  the honest limitation (postal-anchored, not postal-perfect). The fallback is
  NEUTRAL when a postal is absent — absence is never read as contradiction.
- **The ambiguity refusal reads "X and X".** Two character-identical firms produce a
  refusal naming the duplicated display label, which is honest but can look odd. Unit
  4 decides whether to enrich the refusal with a distinguishing locator (city) when
  display names collide — a small business-vertical touch, not an engine change.
- **Touching the frozen core (the generality decision).** Multi-field ER changes
  `resolve_entities` + `resolution.py`, the second sanctioned core delta after M8.
  Defensible (a general ER capability belongs in core; schema stays in the source)
  and recorded in **ADR 0019**, refining ADR 0004's matching method. The leak-guard
  is protected by keeping the address comparison pure-stdlib in `resolution.py`. The
  M9 empty-diff check documents the exact sanctioned delta.
- **Synthetic case-count drift.** Splitting the new pair into two same-named entities
  changes the data-derived synthetic battery count; the count pins
  (`tests/test_synthetic.py`, `tests/test_eval.py`) are updated deliberately in Unit
  4, with the new count explained.
