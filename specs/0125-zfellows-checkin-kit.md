# 0125. Z Fellows check-in kit — the 5-minute arc

- **Phase / milestone:** Milestone 19 Unit 4 (ROADMAP2 M19.5; audience
  calibration: MARKET.md §6, verified). Autonomous per CLAUDE.md. The
  presentation is the maintainer's to deliver; this unit makes rehearsal
  and delivery a read-through, not a writing task.
- **Issue:** —
- **Status:** approved (autonomous mode).

## Problem

The Z Fellows check-in closes the publicly committed one-month build:
live demo → shipped-in-30-days evidence → plan → asks, in five minutes,
to a generalist-SV audience that celebrates working artifacts, committed
users, speed, and storytelling — not enterprise architecture. Improvising
this wastes the month's strongest asset: the recorded, measured trail.

**Recorded decisions:**

1. **Location `launch/zfellows/CHECKIN.md`** — presentation material, not
   system documentation; stays out of the docs-site nav, follows the
   `launch/` publish rule.
2. **The arc is fixed by the kickoff:** Replit story (0:40) → live demo
   over the HF Space, four clicks from DEMO.md §2 (2:00) → what shipped
   in 30 days (1:00) → 3/6/12-month plan (0:50) → asks (0:30). SAP stays
   Q&A material (MARKET §6: the audience is generalist-SV).
3. **Live numbers only:** every traction figure is a `[N]` placeholder
   with the instruction to fill it the morning of the check-in from real
   sources (stars, users, replies, pilots) — never projected, never
   stale. If launch is still pending the maintainer's go, the script says
   exactly that ("staged, ready, waiting on my go") rather than implying
   otherwise.
4. **The honesty rules extend to Q&A:** pocket answers stay inside what
   is measured and recorded (the one real send, the smoke FAIL as the
   battery working, the definitional boundary of the benchmark); the
   "why won't the model vendors do this" answer is positioning, flagged
   as argument rather than fact.
5. **Offline fallback is part of the script:** `tessera-ui` runs every
   demo beat locally with no network; the runbook says to keep it open in
   a second tab throughout (the HF free tier sleeps; a live audience
   never sees a cold start).

## Acceptance criteria

- [ ] `launch/zfellows/CHECKIN.md` — the timed script (all five beats,
      with the words to say), `[N]` placeholders + fill-sources, the
      3/6/12-month plan, the three asks, Q&A pocket answers, logistics
      (rehearsal, screen, fallback).
- [ ] Every number in the script is either measured-and-recorded (with
      its scope) or an explicit placeholder — nothing projected as fact.
- [ ] Gate green; eval byte-identical; no engine/eval change.

## Scope

**In:** the one document.
**Out:** slides (the demo is the deck — beats are clicks); the later
in-cohort presentation (same arc, revisit when scheduled); the demo video
(M17-adjacent, maintainer's, gates nothing); any change to the demo
surface itself.

## Eval impact

None — a document. All six lines byte-identical.

## Risks / open questions

- The check-in **date** is still an open maintainer decision (STATUS);
  the kit is date-independent by construction (placeholders + a warm-up
  checklist rather than a schedule).
- No ADR — freely revisable prose.
