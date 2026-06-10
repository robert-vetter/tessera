# 0023. Trust metrics tracked over time + the earned faithfulness badge

- **Phase / milestone:** Phase 2 — metrics defined, automated, and tracked
  over time
- **Issue:** (none)
- **Status:** implemented

## Problem

The metrics are defined and automated, but each run's numbers vanish with the
terminal: there is no trend, and "visibly improved since Phase 1" (the Phase 2
milestone) has nowhere to be visible. Separately, Phase 0 deliberately
deferred the faithfulness README badge "until the number is real" — it has
been real and gated since Phase 1, so withholding it now would be the inverse
dishonesty.

## Acceptance criteria (decided in autonomous mode)

- [ ] `eval/history.jsonl` — committed, append-only journal of eval runs
      (date, gold + synthetic metrics, free-text note), seeded with the
      phase-1 baseline (marked as retroactively recorded from STATUS).
- [ ] `uv run tessera-eval --record [--note ...]` appends a history entry and
      regenerates `eval/badge.json`; a plain run never writes (CI stays
      read-only).
- [ ] `eval/badge.json` — a shields.io endpoint document for the **gold
      faithfulness** number; green only while the floor holds, red otherwise.
      README shows the badge (label "faithfulness"), replacing the Phase 0
      "deliberately omitted" note; the *coverage* badge stays deferred (no
      code-coverage tooling — that note stays honest).
- [ ] Tests: appending preserves prior lines; badge content/color derive from
      the report; the floor-failed badge is red.

## Scope

**In:** history module, CLI flags, seeded history, badge + README. **Out:**
plotting/dashboards (the JSONL is the auditable source; rendering can come
with the docs site later), code-coverage tooling, automation that records on
every CI run (recording is a deliberate act with a note, not noise).

## Eval impact

None on the numbers; this is where their movement becomes visible. The next
unit (spec 0024) is expected to move coverage 0.938 → 1.000 and the history
will show it — the milestone's "visibly improved" made literal.

## Risks

- A hand-run `--record` can be forgotten — mitigated by the wrap habit
  (record at phase close) and by the badge going stale-visible.
