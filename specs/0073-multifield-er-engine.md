# 0073. Multi-field ER engine: the two-way address gate

- **Phase / milestone:** Milestone 9 — multi-field entity resolution (spec 0072)
- **Issue:** —
- **Status:** approved (autonomous mode; the milestone's project-shaping decisions
  were asked in spec 0072)

## Problem

Spec 0072 settled the design; this unit builds the **engine mechanism**. Today
`KnowledgeGraph.resolve_entities` (`src/tessera/graph.py`) is name-only: a pair is
merged iff `similarity(name_a, name_b) >= threshold` and the M8 stem gate
(`confirm_name_match`) confirms a shared distinctive signal. That leaves the three
Milestone-8 residuals (character-identical firms, two-firm suffix collisions,
double-typo pairs) unreachable.

This unit adds a **second deterministic signal** — corroborating identity fields
(address) the source attaches as node attributes — folded into the existing
name decision as a **two-way gate**. It is the engine half only; wiring the
business graph to pass real address fields is Unit 3 (spec 0074), and the synthetic
disambiguation pair + the measured close is Unit 4 (spec 0075).

## Acceptance criteria

- [ ] **The address-signal helper (`resolution.py`).** A pure-stdlib, embedding-free
      `compare_match_fields(left, right, match_fields)` returns `AGREE` /
      `CONTRADICT` / `NEUTRAL`. `match_fields` are **ordered by decisiveness**: the
      first field present (non-empty) on *both* nodes decides (normalized
      `similarity >= DEFAULT_FIELD_MATCH_THRESHOLD` → agree, else contradict);
      `NEUTRAL` when no field is present on both (absence is never a contradiction).
- [ ] **The two-way gate (`resolve_entities`).** A new **optional** ordered
      `match_fields: Sequence[str] = ()` parameter. For a name-similar pair:
      name-confirmed + address `CONTRADICT` → **veto** (split residuals 1 & 2);
      name-confirmed + `AGREE`/`NEUTRAL` → merge (reason notes any agreement);
      name-vetoed (stem gate) + `AGREE` → **merge** (bridge residual 3, bounded to
      `similarity >= threshold` pairs); name-vetoed + `CONTRADICT`/`NEUTRAL` → veto
      as M8.
- [ ] **None-path byte-identical.** With `match_fields=()` (the devex /
      github_actions default) every assertion — reason string included — is
      byte-identical to Milestone 8. Pinned by a test that a graph carrying address
      attributes but resolved with no `match_fields` ignores them entirely.
- [ ] **`test_scale` residual specimens flip.** The character-identical-firms and
      two-firm-suffix specimens gain addresses + `match_fields` and now assert the
      **split**; each keeps the name-only over-merge as the documented floor in the
      same test, so the cure is visible against the limitation.
- [ ] **Abstract two-way-gate tests** (a new `tests/test_multifield_er.py`): veto on
      contradiction, keep on agreement, bridge a stem-vetoed double-typo pair on
      agreement, and the none-path ignoring address attributes.
- [ ] **Leak-guard green.** The address comparison lives in `resolution.py` (already
      verifier-reachable, stdlib-only); `tests/test_semantic.py` stays green.
- [ ] **ADR 0019** records the design, the two-way gate, the intentional frozen-core
      touch, and the rejected confidence-only alternative.
- [ ] **Pre-merge adversarial multi-agent review** (the M8 discipline) over the
      `graph.py` + `resolution.py` diff; confirmed majors fixed and pinned before
      merge.

## Scope

**In:** the `resolution.py` address-signal helper; the `resolve_entities`
`match_fields` parameter + two-way gate; abstract + `test_scale` tests; ADR 0019.

**Out:** business-graph wiring (`sources/salt.py` + `business/knowledge.py`) is Unit
3; the synthetic disambiguation pair, the new gold case, and the recorded before/after
are Unit 4. No embedding, no cloud. Faithfulness/`is_supported` untouched. Street is
not wired as a decisive field (postal + city carry the signal; street is noisy).

## Eval impact

- **None this unit.** No vertical passes `match_fields` yet, so all three batteries
  read byte-identical to M8 — asserted by the gate (the full eval) staying green and
  unchanged. The measured close lands in Unit 4.
- ER precision/recall (`test_er_metrics`) is touched only in Unit 4 (the
  character-identical-but-different-address pair). This unit pins the *mechanism* on
  abstract graphs.

## Risks / open questions

- **None-path drift (the regression risk).** The reason string must stay
  byte-identical when `match_fields=()`. Mitigation: the address note is appended
  only on `AGREE`; on `NEUTRAL` the string is the exact M8 form, pinned by test and
  by the unchanged batteries.
- **Corroboration adding a wrong merge.** The bridge arm is bounded to
  `similarity >= threshold` pairs, so it cannot reach a *dissimilar*-name pair that
  merely shares a building. The narrow case it *can* reach — two distinct firms that
  are name-similar-but-stem-vetoed **and** share an *exact* address — is a measured
  edge, not a code guarantee (recorded honestly in ADR 0019). The review of this unit
  caught that a fuzzy field ratio made it worse (genuinely different postals scored
  0.909 and falsely AGREE'd); the fix is **exact normalized equality**
  (`DEFAULT_FIELD_MATCH_THRESHOLD = 1.0`), pinned by
  `test_field_match_rejects_postal_substring_collisions`, so only a *genuine*
  same-address pair can bridge — none exists on the synthetic data.
- **Frozen-core touch.** `resolve_entities` + `resolution.py` change — the second
  sanctioned core delta after M8, recorded in ADR 0019. The leak-guard is protected
  by keeping the comparison pure-stdlib in `resolution.py`.
