# 0038. Vertical-owned claim grammars leave eval/metrics.py

- **Phase / milestone:** Phase 4 — platform, polish, and the story (spec 0035 Unit 4)
- **Issue:** —
- **Status:** approved (autonomous mode; ADR 0011 records the mechanism decision)

## Problem

ADR 0008 named it plainly: verifier shapes 2–5 in `eval/metrics.py` encode the
**business vertical's claim grammar** ("net order value", customer/address
record counts, the renewal-date conflict — it even imports
`tessera.business.conflicts`). That was an acknowledged, recorded leak,
"scheduled for the Phase 4 relocation rather than churned mid-proof." This
unit pays it off: the faithfulness verifier's *core* keeps only the grammars
that are genuinely vertical-neutral (verbatim containment, the shared-fragment
shape), and each vertical owns the grammars of the claims only it composes —
carried to the harness explicitly by its `Battery` (the ADR 0009 wiring
pattern), never discovered dynamically.

## Acceptance criteria

- [ ] `tessera/business/claims.py` holds the five business grammars (compare,
      superlative, conflict disclosure, aggregate recomputation, count match,
      refuse-to-sum) as tri-state shape functions (`bool` = owned verdict,
      `None` = not my grammar), moved logic-identical from `eval/metrics.py`.
- [ ] `eval/metrics.py` contains **zero vertical vocabulary**: the `ClaimShape`
      contract, the generic shared-fragment grammar, generic verbatim
      containment, and the `is_supported` orchestration (battery shapes in
      declared order → shared fragment → containment → unsupported).
- [ ] `Battery` gains `claim_shapes: tuple[ClaimShape, ...] = ()`; the harness
      passes them; the business battery declares its six shapes; the devex
      battery declares none (its claims are verbatim snippets + the generic
      shared-fragment grammar — that fact is itself part of the generality
      story).
- [ ] Every adversarial verifier test survives (injected lies still caught),
      updated to exercise business grammars through the explicit shapes.
- [ ] **Both batteries' numbers byte-identical** (7/52, 7/24, all 1.000); no
      `--record`.
- [ ] ADR 0011 records the mechanism and the one deliberate precedence change
      (a vertical conclusion grammar now owns its verdict ahead of generic
      containment — stricter, never laxer, and measured to change nothing).

## Scope

**In:** the verifier split, battery plumbing, registry wiring, test updates,
ADR 0011 (+ index/nav), an ADR 0008 addendum closing the recorded leak.

**Out:** new grammars or grammar changes (logic moves verbatim); plugin/entry-
point discovery (rejected again — ADR 0008's argument stands; the registry's
explicit tuple is the whole mechanism); changing scoring semantics (faithfulness
remains "fraction of claims with deterministically verified support").

## Eval impact

None — pinned. The point is *where the grammars live*, not what they verify.

## Risks / open questions

- Precedence: shapes 4/4b/etc. previously ran after generic containment; now
  battery shapes run first. For owned-verdict grammars this is stricter (a
  failed conclusion can no longer be rescued by being a verbatim substring).
  No corpus claim hits the difference (verified by the pinned numbers and the
  adversarial suite); recorded in ADR 0011.
- The `ClaimShape` signature (`claim, nodes, graph -> bool | None`) must stay
  vertical-neutral; a grammar needing more context than that is a design smell
  to stop and record, not to plumb through.
