# 0047. Mixed-modality multi-hop in one turn: the RCA fix chain

- **Phase / milestone:** Milestone 5 — Hardening (spec 0043, unit 5)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

The Phase-2 milestone check named an honest gap and carried it forward: *"deeper
mixed-modality multi-hop in one question"* was not done. RCA stopped at the
documented incident ticket; it never crossed to the **PR that resolved that
incident** or the **diff that did it**. A user asking *"why did run R-1042 fail,
and how was it fixed?"* got the failure story but not the fix.

The data to walk it has sat in the committed corpus since Phase 3: the incident
`DEVEX-187` is resolved by `PR-198` (whose description "Fixes DEVEX-187" already
became a `motivated_by` edge at ingestion), and `PR-198` carries the actual diff
(`timeout=10` → `timeout=30`). One more hop turns RCA into a genuine
**row → log → prior log → ticket → PR row → diff** chain, each hop individually
cited.

The hazard is the **mis-pivot trap**: `PR-201` fixes the *follow-up* `DEVEX-204`,
not the incident `DEVEX-187`. A naive "any related payments PR" chain would cite
`PR-201` and emit an unsupported attribution — which the faithfulness verifier
would (correctly) reject. The fix must follow the **exact** ticket-id edge.

## Acceptance criteria

- [ ] `explain_failure` is extended: for each documented-incident ticket, it
      surfaces the PR(s) that resolve it (via the reversed `motivated_by` edge —
      the exact ticket id), as a neutral shared-fragment claim (the ticket id
      appears in both records), plus the PR row and its diff hunks. All
      vertical-side; `graph.py`/`grounding.py`/`metrics.py` untouched.
- [ ] The mis-pivot is avoided **structurally**: `DEVEX-187`'s chain cites
      `PR-198` and never `PR-201` (a test pins this).
- [ ] Honest omission holds: an **open** incident with no resolving PR
      (`DEVEX-231`) stops at the ticket — no "Resolved by" is invented.
- [ ] Every chain claim passes the faithfulness verifier (covered by the
      existing all-claims verifier test, which includes R-1042).
- [ ] A new gold case `08_r1042_fix_chain` pins the full chain; **devex gold
      8/8 stays faithfulness 1.000, coverage 1.000, quality 1.000**, and the
      business, devex-synthetic, and github_actions numbers are **unchanged**
      (the extension only *adds* faithful claims).

## Scope

**In:** the incident→fixing-PR→diff hop in `devex/rca.py`; gold case 08; the
chain / mis-pivot / honest-omission tests.

**Out:** the second-level follow-up hop (`DEVEX-187` → follow-up `DEVEX-204` →
`PR-201`) — deliberately not walked; it needs a "follow-up" edge and risks
exactly the over-attribution the mis-pivot test guards against, so it is left as
honest future depth (the engine surfaces the *direct* fix, not speculative
follow-ups). The commit-join hop (PR → shipped-in run) — also deferred. Intent
phrasing ("…and how was it fixed?" is not parsed; the chain is included whenever
available) — that is the router's ceiling, spec 0048. A business
second-entity-from-clause pivot — out (this unit is the devex chain; the
business multi-hop is a candidate for a later milestone, named in the WRITEUP).

## Eval impact

devex gold 7 → **8** cases, all metrics **1.000** (the new chain case is fully
covered). All other recorded numbers unchanged. Faithfulness 1.000 everywhere.
The point is not a moved number — it is a **capability** (a real multi-hop answer)
that the gold set now pins and the verifier guards.

## Risks / open questions

- **Behaviour enrichment, not a new path:** every failed run that reaches a
  resolved incident now also surfaces its fix. Existing gold/synthetic devex
  cases are supersets-safe (their expectations are subsets), verified by the
  unchanged numbers — but this is the kind of broad change to watch, so the
  before/after eval is pinned in the gate.
- **Engine-leak guard:** the hop uses only `graph.sources_of`/`graph.node`
  (existing primitives); no traversal helper leaks into the frozen core
  (ADR 0008). Re-checked at the milestone close by the empty-diff audit.
