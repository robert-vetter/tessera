# 0034. Phase 3 close: docs, drift repair, the core-frozen audit, the tag

- **Phase / milestone:** Phase 3 — second vertical (DevEx Copilot), Unit 9
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

The phase is functionally complete and measured; what remains is making the
repo *say so* truthfully (CLAUDE.md: "the docs reflect reality") and closing
with the audit that turns the milestone into evidence.

## Acceptance criteria

- [ ] README: the two verticals (both runnable, both measured), the
      two-battery eval output, the DevEx demo section, the devex corpus in
      the data section, the badge's new (min-across-batteries) meaning.
- [ ] CHANGELOG: Phase 3 section written; the lingering Phase 2 entries
      rolled into their own section (drift repair, noted honestly).
- [ ] **Core-frozen audit recorded in STATUS**: `git diff phase-2..HEAD`
      over the ADR 0008 frozen list is empty; only the two sanctioned eval
      deltas exist.
- [ ] Full gate + eval green under multiple `PYTHONHASHSEED` values.
- [ ] STATUS wrap entry; tag `phase-3` after merge.

## Scope

**In:** docs, CHANGELOG, STATUS, audit, tag.
**Out:** new behaviour of any kind.

## Eval impact

None — numbers stand as recorded by Unit 8.

## Risks / open questions

None — closing chores only.
