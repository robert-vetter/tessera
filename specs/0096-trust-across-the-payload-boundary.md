# 0096. Trust across the payload boundary (the gated property)

- **Phase / milestone:** Milestone 13 (spec 0093), Unit 4.
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

Units 2–3 render and transport a dry-run payload. This unit *measures* the trust
contract across the payload boundary — the payload-level analogue of
`tests/test_boundary.py` (M11) and `tests/test_actions_boundary.py` (M12). Over cases
**derived from the data** (every failed run → an incident payload; every PR → a
pr_summary payload; anti-tautology, ADR 0007), a pinned CI test asserts the rendered
payload is field-grounded, lossless, and adds nothing — so the new capability's effect
on the metric is *known* (principle 3), not assumed.

## Acceptance criteria

- [ ] `tests/test_payloads_boundary.py`, offline + pure-stdlib (drives
      `preview_payload`, no SDK), runs in the gate.
- [ ] **Field-grounded + lossless:** for every derived case the payload is `rendered`
      and `all_grounded`; each non-path content slot is exactly one of the proposal's
      verified fields (same value, support ids, and the **independently recomputed**
      verdict); the `{pr}` resource slot (pr_summary) traces to the subject's PR record;
      nothing added, dropped, or relabeled into a false verdict.
- [ ] **Faithfulness 1.0 across the payload boundary:** counted over every content slot
      of every derived payload, every slot is verifier-passing; and the wire request is
      **byte-reconstructable** from the verified fields plus the declared scaffolding (an
      independent rebuild, so a fabricated/over-claimed/smuggled value fails it).
- [ ] **A withheld payload carries no request:** a passed/unknown run, an out-of-scope
      question, an incompatible route, and a wrong domain each yield `rendered=False`
      with an empty request and `withheld_reason` — never a payload over ungrounded
      ground.
- [ ] **ADR 0005/0006 re-examined at the payload boundary and recorded still not
      forced** (a documentation-pin test): every slot's verdict is the same structural
      `is_supported` the eval gates on (no semantic judge); rendering is deterministic
      templating over verified fields (no LLM, no semantic routing).

## Scope

**In:** the data-derived boundary test and its three gated properties + the ADR
re-examination pin.

**Out:** new product code (Units 2–3 shipped it); a new gated eval metric (this is a
*pinned* property, the M11/M12 pattern; faithfulness stays the single floor); the close
(Unit 5).

## Eval impact

- **Faithfulness — held at 1.0, now also across the payload boundary** (measured here,
  not assumed). Coverage/quality unchanged (the payload layer is a consumer).
- **No new gated metric** — the property is pinned; faithfulness remains the one floor.

## Risks / open questions

- **The measurement must be able to fail.** It recomputes each slot's verdict
  independently (not read from the payload) and rebuilds the wire request independently,
  mirroring the M11/M12 boundary tests; a drafter/renderer that fabricated, over-claimed,
  or smuggled a value would fail. The Unit-2 provably-failable tests back this up.
- **Data-derived, so it widens with the corpus** — a new failed run or PR adds a case
  automatically (anti-tautology).
