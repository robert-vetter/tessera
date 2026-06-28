# 0075. The synthetic disambiguation pair + the measured before/after close

- **Phase / milestone:** Milestone 9 — multi-field entity resolution (spec 0072)
- **Issue:** —
- **Status:** approved (autonomous mode; scope question (c) was asked in spec 0072)

## Problem

This is the milestone's **headline**. Units 2–3 built and wired multi-field ER but
left the existing numbers byte-identical (no character-identical distinct firm exists
in the corpus yet). This unit adds one — two genuinely distinct firms sharing an
identical name at different addresses — so the fix becomes a **measured eval
before/after** (the Milestone-5/6/7 "measured miss → measured close" discipline):

- **Before (name-only ER):** the two firms over-merge into one cluster, so the
  ambiguous-name question resolves to a single (wrong) entity and **answers** it —
  where the correct behaviour is to **refuse as ambiguous**. A measured **quality**
  miss (faithfulness still 1.0 — the answer is faithful to the wrong cluster).
- **After (multi-field ER):** the address splits the two firms into two entities with
  the same display name, so the question correctly **refuses** — the system catches
  its own over-merge. Quality restored to 1.0, **CI-reproducible** (unlike the M6/M7
  online closes).

## Acceptance criteria

- [ ] **The disambiguation pair (generator).** Two `Hanseatic Trading GmbH` customers
      at different addresses (Hamburg / Munich, distinct postals) appended to
      `scripts/generate_salt_synthetic.py` as **fixed rows after the Atlas section**
      (outside the RNG stream), reserved ids `0010000009`/`0010000010`,
      `A0009`/`A0010`. **No sales orders** (the ER demo needs only customer + address;
      orders would create a same-name synthetic compare case). Data regenerated;
      **existing rows byte-identical** (the diff is pure additions); MANIFEST counts
      updated by the generator.
- [ ] **The over-merge → split is real, pinned.** A test asserts name-only ER merges
      the two firms (the miss) and multi-field ER splits them (the close) on the
      *demo* graph; the cluster-equivalence pin (Unit 3) is updated to reflect the one
      intended new split (the business graph now has one more cluster than name-only).
- [ ] **The measured gold case.** A new business gold case (`kind: refuse`,
      `engine: compose`) asks the ambiguous-name question; under multi-field ER it
      **refuses** (correct). A test measures both arms over the gold set: name-only
      quality `0.900` (the miss) vs multi-field `1.000` (the close).
- [ ] **Recorded before/after in `eval/history.jsonl`.** Two points: name-only
      (business gold quality `0.900`, faithfulness `1.000`) and multi-field (business
      gold quality `1.000`), each `--note`-paired, via a one-shot measurement over a
      name-only battery (`run_eval` accepts a custom battery list).
- [ ] **Synthetic battery count updated.** The split adds exactly one ambiguous-token
      refuse case (`Trading`, now shared by Atlas + the two Hanseatic firms); the
      count pins (`tests/test_synthetic.py`, `tests/test_eval.py`) move `52 → 53`,
      explained. Faithfulness stays 1.0 on every battery.
- [ ] **ER metric note updated.** The `test_er_metrics` docstring residual note (the
      character-identical floor) is updated — multi-field ER now closes it.
- [ ] Gate green and deterministic across `PYTHONHASHSEED`; devex/github_actions
      untouched.

## Scope

**In:** the generator's disambiguation pair + regeneration; the gold case; the
before/after measurement + history points; the count-pin + docstring updates; tests.
**Out:** WRITEUP/README/CHANGELOG/STATUS/tag (Unit 5 close). No embedding, no cloud.

## Eval impact

- **business gold quality 0.900 (name-only) → 1.000 (multi-field)** — the headline,
  both points recorded, the *after* CI-reproducible.
- **business synthetic 52 → 53 cases**, all 1.000 (the new ambiguous-token refusal is
  correctly refused).
- **Faithfulness 1.000 throughout** (the floor holds in both arms — the name-only
  wrong answer is still faithful to its merged cluster; the gate measures structure,
  not the right entity). devex/github_actions unchanged.

## Risks / open questions

- **The pre-fix answer must be grounded** (so the refuse-kind gold case scores a real
  miss). Verified empirically: name-only compose over the merged Hanseatic cluster
  produces a grounded identity answer; multi-field makes it an ambiguous refusal.
- **Generator determinism.** The pair is appended outside the RNG stream (the Atlas
  pattern), so existing rows stay byte-identical — verified by `git diff` being pure
  additions, not a re-randomisation.
- **`corpus_generic_tokens` perturbation.** Two same-named firms could in principle
  push `trading` to `min_df`; but the remove-then-count-*distinct-firms* definition
  (ADR 0018) sees them as one distinct firm (`hanseatic`), so `trading` spans
  {atlas, hanseatic} = 2 < 3 and stays distinctive — re-verified by the
  cluster-equivalence pin after the data lands.
- **Honest "before".** The name-only point is a counterfactual baseline (the M9 data
  did not exist at M8), recorded with a note that says so — the measured prior-engine
  limitation over the new data, not a claim that this exact state shipped.
