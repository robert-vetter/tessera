# 0110. Milestone 16 Unit 3: verifier honesty (B6–B7)

- **Phase / milestone:** Milestone 16 (Act 2 opener), Unit 3 — see spec 0107 and
  [`docs/AUDIT_2026-07-02.md`](../docs/AUDIT_2026-07-02.md) §3–4.
- **Issue:** —
- **Status:** implemented

## Problem

The audit named verifier blind spots that were *true but unstated*: the generic
containment grammar does not penalize over-citation (B6a) and matches across
word boundaries after normalization (B6b); and refuse-kind eval cases skipped
faithfulness accounting entirely (B7) — a wrongly-answering refuse case could
emit claims no verifier ever checked. A trust metric's limits must be as
documented as its guarantees.

## Acceptance criteria

- [x] **B7 fixed, transparently:** `eval/harness.py::_score` runs the per-claim
      faithfulness check for **every** case kind; refuse-kind handling keeps its
      quality semantics. Measured effect: **all six battery lines
      byte-identical** (the change widens what is counted, not what passes);
      the previously-unreachable failure mode can now fail the floor.
- [x] **B6 named, with committed specimens** (the ADR 0005 pattern): an
      over-citation specimen (decorative citation passes; missing support still
      fails) and a cross-word-boundary containment specimen, both in
      `tests/test_trigger_specimens.py`.
- [x] **ADR 0005 addendum** records both blind spots, the B7 accounting change
      with its measured zero effect, and the recorded future work (a reported —
      not gated — over-citation strictness metric).
- [x] Gate green; eval floors unchanged.

## Scope

**In:** the harness accounting change, the two specimens, the ADR addendum.
**Out:** changing `is_supported` semantics (the gated metric's definition is
untouched); an over-citation metric (recorded future work); any battery/gold
change. Decision (spec 0107, recorded): this unit carries the measured
no-change proof instead of a multi-agent review — the gated metric's
*definition* is unchanged; only its accounting coverage widened.

## Eval impact

Intended none, proven: every battery number byte-identical before/after. The
floor's reach widened (refuse-kind claims are now inside it) — a strictness
increase with zero measured movement on current data.

## Risks / open questions

- A future battery whose correct refusals carry claims (partial answers) will
  see its claim counts rise — the ratio only moves if such a claim is
  unfaithful, which is exactly the point.
- The named blind spots remain: the specimens make them precise; acting on
  them stays tied to a measured miss (the ADR 0005 discipline).
