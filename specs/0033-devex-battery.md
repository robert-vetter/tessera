# 0033. The DevEx battery: gold set, synthetic cases, first two-vertical numbers

- **Phase / milestone:** Phase 3 — second vertical (DevEx Copilot), Unit 8
- **Issue:** —
- **Status:** approved (autonomous mode; decisions recorded here)

## Problem

The DevEx vertical exists but is not yet *measured* — and per principle 3,
unmeasured means unfinished. This unit gives the vertical its curated gold
set and its enumerated synthetic battery, binds it into the eval registry,
and records the project's first two-vertical numbers.

## Acceptance criteria

- [ ] `eval/gold/devex/` (7 curated cases): the flagship RCA-with-recurrence
      case, the PR-201 change summary, an on-call lookup, the **named
      coverage miss** (the notifications on-call row is unreachable —
      `notif-svc` resolves at 0.429 and shares no retrieval token with the
      question), and three refusal kinds (passed run / unknown run /
      out-of-corpus).
- [ ] `tessera/devex/synthetic.py` — enumerated from the graph,
      deterministic, expectations **data-derived** (ADR 0007): an RCA case
      per failed run (expected support: the run row + its error-bearing log
      chunks; expected facts from the run's own attributes), a
      refused-premise case per passed run, a summary case per PR (expected
      support: row + hunks + referenced ticket, parsed from the row text),
      unknown-id refusals, and vocabulary-checked missing-evidence
      templates.
- [ ] `eval/registry.py` binds the devex battery; the floor now gates four
      numbers (business/devex × gold/synthetic).
- [ ] Numbers recorded: `tessera-eval --record --note …` appends the first
      v2 history line; the badge stays the min gold faithfulness.
- [ ] Expected outcome, stated upfront: **faithfulness 1.000 everywhere**
      (gated); **devex gold coverage ≈ 0.917** — the named miss, kept, not
      patched (it is the measured trigger ADR 0003/0004 have been waiting
      for); quality 1.000.

## Scope

**In:** gold cases, the generator, registry binding, tests, the recorded
run.
**Out:** *fixing* the named misses (that is the next trust-improvement
loop, driven by this number — exactly how the Lumière gap was handled in
Phase 2); paraphrase variants (ADR 0007's documented blind spot stands).

## Eval impact

The headline of the phase: a second vertical measured by the same harness
under the same floor. DevEx coverage deliberately lands < 1.0 with a named,
recorded cause.

## Risks / open questions

- Synthetic RCA expectations avoid re-deriving the signature with the
  engine's own regex (tautology risk, ADR 0007); facts come from run
  attributes, support from log text containment — both data, not engine
  output. Recurrence-claim correctness is stressed by faithfulness (every
  claim is verified), not by echoed expectations.
