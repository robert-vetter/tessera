# 0086. Milestone 11 close

- **Phase / milestone:** Milestone 11, Unit 6 — the close (see spec 0081)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018)

## Problem

Milestone 11 (agentic / MCP-exposed grounded mode) is functionally complete across
Units 1–5: the heading-chunk fix (0082, ADR 0021), the grounded-tool layer (0083,
ADR 0022), the MCP server (0084), and the boundary-trust measurement (0085). The
project's definition of done (CLAUDE.md) requires the docs to reflect reality, the
generality/empty-diff audit to be recorded, the eval numbers to be known, and a
stranger to be able to follow what changed and why. This unit closes the loop.

## Acceptance criteria

- [ ] **Frozen-core empty-diff audit recorded.** `git diff milestone-10..HEAD` over
      the ADR 0008 frozen list is empty **except** `ingestion.py` (the ADR 0021
      heading-merge, the one sanctioned delta). Verified per-file (the verifier
      `eval/metrics.py`, `graph.py`, `resolution.py`, and the rest are empty-diff —
      the leak-guard holds; faithfulness stays structural).
- [ ] **WRITEUP** gains the Milestone-11 section (the agentic boundary, the
      boundary-trust measurement, read-only scope), updated limitations (the
      read-only agent boundary + the router/engine ambiguity gap), updated
      future-work (read-only MCP now exists; grounded *actions* + router-ambiguity
      alignment are the next steps), a 9th "what was learned", and the MCP doors in
      the reproduce block.
- [ ] **README** corrects the reverse-overclaim (read-only MCP now exists, not
      "future work"), adds the agent-surface (MCP) section, and fixes the stale
      business gold count (10 → 11).
- [ ] **CHANGELOG** `[milestone-11]` section; **ADR index + mkdocs nav** for 0021 and
      0022; **STATUS** entry; this spec.
- [ ] Gate green under multiple `PYTHONHASHSEED` values; faithfulness 1.0 on all
      batteries; `tag milestone-11`; memory updated; next-milestone kickoff handed back.

## Scope

**In:** the docs close (WRITEUP/README/CHANGELOG/STATUS), ADR nav/index, the
frozen-core audit record, the tag, memory, the kickoff.

**Out:** any code change (the milestone's code shipped in Units 2–5); fixing the
router-ambiguity gap or adding grounded actions (recorded future work).

## Eval impact

- **None** — docs/close only. Faithfulness stays 1.0 on all three batteries; the
  boundary-trust measurement (Unit 5) is the recorded "effect on the metric is known".

## Risks / open questions

- **Reverse-overclaim risk.** The README/WRITEUP previously named agentic/MCP as
  future work; this close must update those to the truthful "read-only MCP exists;
  grounded actions are next" — the same honesty discipline that removed the *forward*
  overclaim in Phase 4 (spec 0042). Done.
- **The recorded next levers must be honest and specific** (not vaporware): grounded
  actions (effectful / propose-and-approve), router-ambiguity alignment with
  `compose`, a second real connector (Jira), and the still-live ADR 0005/0006
  triggers. Each named with its condition.
