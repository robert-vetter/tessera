# 0091. Trust across the action boundary: field-grounded, lossless, faithful

- **Phase / milestone:** Milestone 12, Unit 5 (plan: spec 0087)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

Units 3–4 built the grounded-action layer and exposed it over MCP. The milestone's
success criterion (spec 0087) is that the **trust contract is *measured* to survive the
action boundary**, the way Milestone 11 measured it for answers
(`tests/test_boundary.py`: faithfulness 1.0, lossless projection, refusals preserved).
This unit lands that measurement for actions: a pinned, CI-gated property over
representative cases, so the new capability's effect on the metric is *known* (principle
3), not assumed.

## The design

`tests/test_actions_boundary.py` — the action-level analogue of `test_boundary.py`,
**offline and pure-stdlib** (it drives `ground` + `draft_action`, no SDK), so it runs in
the gate. Cases are **data-derived** (anti-tautology, ADR 0007 discipline): every failed
run in the devex and real `github_actions` graphs yields an `incident` case; every PR in
the devex graph yields a `pr_summary` case (14 cases today: 9 incidents, 5 PR summaries).

Three measured properties:

1. **Field-grounded + lossless.** For every derived case the proposal is `grounded` and
   `all_grounded`; each non-title field is a *lossless projection* of exactly one
   grounded claim — same value (the claim's verbatim text), same support ids, and the
   **same verifier verdict** the engine's boundary `is_supported` produced (recomputed
   independently here, not read from the proposal); the optional title is a verbatim
   fragment of a grounded claim's own evidence and is verified. Nothing is added, dropped,
   or relabeled into a false verdict.
2. **Faithfulness is 1.0 across the action boundary.** Counted over every field of every
   derived case: every field is verifier-passing. This is the headline gated property —
   the M11 boundary-equivalence pattern, at the action level. A drafter that fabricated or
   over-claimed a field would drop the count below 1.0 and fail.
3. **A refusal is carried, never drafted.** Over refusal-inducing inputs — a run that
   *passed*, an unknown run (synthetic and real), an out-of-scope question, an
   incompatible route (incident from a PR question), a wrong domain — the proposal is
   `refused` with no fields. An action is never proposed on ungrounded ground.

**ADR 0005/0006 re-examined at the action boundary and recorded *not forced*** (a
documentation pin, mirroring `test_boundary.py`): the structural verifier produced every
field verdict across the boundary with no case it missed (0005 unforced), and drafting is
deterministic selection/templating over verifier-passing claims — not LLM generation or
semantic routing (0006 unforced).

## Acceptance criteria

- [ ] `test_actions_boundary.py` derives incident cases from every failed run (devex +
      github_actions) and pr_summary cases from every devex PR; asserts each is
      field-grounded and a lossless projection of its grounding (value, support ids, and
      independently-recomputed verdict per field).
- [ ] A counted property: faithfulness == 1.0 across the action boundary (every field of
      every derived case verifier-passing); `total > 0`.
- [ ] A refusal arm: passed/unknown/out-of-scope/incompatible-route/wrong-domain inputs
      each yield a carried refusal with no fields.
- [ ] ADR 0005/0006 re-examined and recorded not forced (a documentation-pin test).
- [ ] Gate green under multiple `PYTHONHASHSEED` values; faithfulness 1.0 on every
      battery; no battery number moves. Faithfulness stays the single hard gate (this
      property is *pinned*, not a new gated metric — the M11 pattern).

## Scope

**In:** `tests/test_actions_boundary.py` (the data-derived cases + the three properties +
the ADR pin). No production code changes — this unit *measures*.

**Out:** any change to the drafting logic or the MCP tools (Units 3–4, unchanged); a new
gated eval metric (faithfulness stays the single floor; field-grounding is pinned, not
gated); any engine or frozen-core change; the close (Unit 6).

## Eval impact

**None to the gated numbers.** The measurement is a pinned CI test, not a new battery or
gate. Faithfulness stays 1.0 on every battery; no battery number moves. The *new* recorded
property is "faithfulness 1.0 across the action boundary" — the M11 pattern for actions.

## Risks / open questions

- **Tautology risk.** Mitigated by deriving cases from the graphs (not hand-picking) and
  by recomputing each field's verdict against the grounding independently — the property
  is *measured*, not asserted by reading the proposal's own flags. The per-field
  provably-failable proof already lives in `tests/test_actions.py` (spec 0089), so the
  verdict the boundary trusts is itself earned.
- **Coverage drift.** The case set grows with the corpus (every failed run / PR), so the
  measurement widens automatically as data is added — no silent cap.
