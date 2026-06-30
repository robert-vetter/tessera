# 0092. Milestone 12 close: grounded actions over MCP

- **Phase / milestone:** Milestone 12, Unit 6 (plan: spec 0087)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

Units 1–5 delivered grounded actions over MCP: the plan (0087) and its three recorded
scope decisions; router-ambiguity alignment (0088); the grounded-action layer (0089, ADR
0023, with a pre-merge adversarial review and two fixes pinned); the MCP `list_actions`/
`draft_action` tools and a committed client session (0090); and the action-boundary
measurement (0091). This unit closes the milestone: prove the invariants, reflect reality
in the docs, tag, and hand back a kickoff.

## Acceptance criteria

- [ ] **Frozen-core empty-diff audit** (ADR 0008) over `milestone-11..HEAD` is empty —
      the action layer is additive (`tessera/agent/`), the only existing-code production
      change is the vertical-side router fix (Unit 2, reviewed). Recorded here.
- [ ] **Gate green under multiple `PYTHONHASHSEED` values**; faithfulness 1.0 on every
      battery; no battery number moved.
- [ ] **WRITEUP** gains a "grounded actions over MCP" section (the drafter, the
      field-grounding/lossless measurement, the propose-and-approve scope + deferred
      execution, the still-live ADR 0005/0006 triggers) + updated limitations/future-work
      + a 10th "what was learned".
- [ ] **README** documents the action tools and the corrected scope (read-only actions
      are *proposed* and field-verified; execution stays out — the honest edge).
- [ ] **CHANGELOG** `[milestone-12]` section.
- [ ] **ADR 0023** added to the mkdocs nav and the `docs/adr/README.md` index.
- [ ] **STATUS** Milestone 12 close entry; **tag `milestone-12`**; **memory** updated;
      **next-milestone kickoff** handed back.

## Scope

**In:** docs only (WRITEUP, README, CHANGELOG, STATUS, ADR nav/index), the empty-diff
audit, the tag, memory, the kickoff. **Out:** any code change (the milestone's code is
done and merged); a new gated metric; a new milestone's work.

## Eval impact

None — a documentation/close unit. Faithfulness stays 1.0 on every battery; the recorded
M12 property is "faithfulness 1.0 across the action boundary" (spec 0091), already landed.

## Risks / open questions

- **Overclaim risk at the close.** The README/WRITEUP must say exactly what shipped:
  *propose-and-approve, field-verified action drafts* — nothing executed. The honest edge
  (the agent still acts outside Tessera) is named, not glossed.
