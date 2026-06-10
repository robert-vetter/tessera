# 0018. Autonomous phase execution mode

- **Phase / milestone:** Phase 2 — process prerequisite (anti-drift)
- **Issue:** (none)
- **Status:** implemented

## Problem

Phases 0–1 ran the loop interactively: the maintainer approved every `/spec` and
`/plan` by hand, unit by unit. That cadence is too slow for the remaining
phases, and the maintainer has asked for phases to run **autonomously**: one
kickoff prompt, the whole phase executes, decisions are made and *recorded* on
the way. The discipline must not weaken — specs, ADRs, the verify gate, PRs and
CI stay exactly as they are; only the interactive approval stops are removed.
This unit codifies that mode in `CLAUDE.md` so any future session (human or
agent) runs it the same way, and fixes two pieces of docs drift found while
auditing the repo state: ADRs 0002–0005 are missing from the docs-site nav, and
the CHANGELOG was never updated for Phase 1.

## Acceptance criteria

- [ ] `CLAUDE.md` documents autonomous phase execution: unchanged artifacts
      (spec per unit, ADR for hard-to-reverse choices, gate + eval green,
      branch→PR→CI→merge), self-approved decisions recorded in the spec/ADR,
      user questions reserved for genuinely project-shaping calls, `/wrap` +
      phase tag at the end.
- [ ] mkdocs nav lists ADRs 0002–0005; strict docs build green.
- [ ] CHANGELOG `[Unreleased]` honestly reflects Phase 1 (cross-checked against
      merged PRs #10–#21).

## Scope

**In:** the CLAUDE.md section, mkdocs nav, CHANGELOG catch-up. **Out:** any
engine code; changing the loop's artifacts themselves; rewriting commands.

## Eval impact

None — process/docs only. The eval continues to run in every unit's gate.

## Risks / open questions

- Autonomy can hide bad judgment; mitigation is unchanged artifacts — every
  decision still lands as a written spec/ADR + PR that can be reviewed after
  the fact, and `/audit` stays in the toolkit.
