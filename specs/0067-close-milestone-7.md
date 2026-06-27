# 0067. Close Milestone 7: docs, generality proof, tag

- **Phase / milestone:** Milestone 7 — Unit 8 (of spec 0060)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

The seven prior units built and recorded both M7 capabilities (embedding-assisted
ER, finer log chunking) and the online closes. This unit makes the milestone
legible to a stranger and verifiable as done: docs reflect reality, the engine
stays general, the offline path is deterministic, and the milestone is tagged.

## Acceptance criteria

- [ ] **WRITEUP** gains a Milestone-7 section (the two wins, the stem-gated ER
      design, the recorded online numbers, the earned-not-saturation precision
      result, the asymmetric-embedding finding, the over-merge residual); the
      limitations + future-work sections updated (ER recall now embedding-assisted;
      the over-merge residual + its next lever; both closes are link-only, online).
- [ ] **README** numbers updated (devex gold 0.950, github_actions gold 0.833,
      both online closes explained, faithfulness still the gated floor).
- [ ] **CHANGELOG** `[milestone-7]` section; STATUS journal entry.
- [ ] **Generality proof**: `git diff milestone-6..HEAD` over the ADR 0008 frozen
      core list is **empty** (all M7 work is additive — a new module, vertical-side
      application, source-level chunking).
- [ ] **Determinism**: the offline gate is byte-identical under multiple
      `PYTHONHASHSEED` values (0/1/2026).
- [ ] **Tag `milestone-7`**; memory updated; a paste-ready next-milestone kickoff
      handed back.

## Scope

**In:** WRITEUP/README/CHANGELOG/STATUS, the empty-diff + determinism checks, the
tag, memory. **Out:** any new capability; the over-merge residual's fix (the named
next-milestone candidate).

## Eval impact

None — documentation + verification only. Numbers are as Units 6–7 left them
(offline misses in CI; online closes recorded).

## Risks / open questions

- The milestone's honest residual (the additive ER regime can't cure `difflib`'s
  over-merge) is stated at full prominence in the WRITEUP and STATUS, with its
  next lever named — not buried.
