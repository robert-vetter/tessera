# 0124. Launch & outreach kit — drafted, not sent

- **Phase / milestone:** Milestone 19 Unit 3 (ROADMAP2 M19.3–M19.4;
  playbook + targets: MARKET.md §5). Autonomous per CLAUDE.md; every piece
  here is a **draft** — publishing and sending are the maintainer's acts,
  under his identity and timing.
- **Issue:** —
- **Status:** approved (autonomous mode).

## Problem

The launch (Show HN + community posts) and the outreach wave (100–150
personalized DACH consultancy messages, 3–4 touches, offering the M18
pilot) are M19's traction engine. Both fail when improvised at send time:
posts drift into overclaim under deadline pressure, outreach devolves into
generic spam, and nobody tracks touches. This unit commits the whole kit —
in the maintainer's first-person voice, honesty-guarded now while the
measured facts are fresh — so "go" costs minutes.

**Recorded decisions:**

1. **Layout:** `launch/posts/` (Show HN + planned first comment +
   known-attack prep; r/LLMDevs; X thread; channel notes) and
   `launch/outreach/` (DE/EN touch sequence, pilot success definition,
   call script, tracking scaffold). The M18 pilot
   ([docs/PILOT.md](../docs/PILOT.md)) is the single offer everywhere.
2. **Privacy line for the target list:** the committed
   `targets.example.csv` carries **company-level rows only**, all already
   public in MARKET.md §5 (with the public signal that put them there);
   person-level fields stay empty. The working `targets.csv` (names,
   contacts, dates) is **gitignored** — a public repo never carries an
   individual's outreach pipeline.
3. **Numbers in drafts are dated, not pinned.** Posts quote benchmark
   results with their scope (offline, our corpora) and carry a
   "verified 2026-07-03 — re-run `tessera-benchmark` before publishing"
   header instead of CI pins: drafts get edited at send time, and
   `docs/BENCHMARK.md` (CI-pinned) stays the public source of truth the
   posts link to.
4. **Honesty guards baked into the copy:** the Show HN body names the
   limits (deterministic answer layer, our corpora, two measured BYO
   repos, the third-repo smoke FAIL as a feature) before any commenter
   digs for them; the known-attack prep includes the benchmark's
   definitional boundary (the structural-notes story from the spec 0122
   review) so the maintainer never defends the artifact beyond what it
   proves; no post claims users/pilots that don't exist; never
   "hallucination-free".
5. **Sequencing doctrine recorded, not scheduled:** Show HN first (its
   thread is the anchor link), satellites within 24–48h, outreach runs
   independently of launch outcome (MARKET: design partners come from
   outreach, not HN).

## Acceptance criteria

- [ ] `launch/posts/show-hn.md` — title (≤80 chars), body, planned first
      comment, known-attack prep including the definitional-boundary
      answer, prereq checklist (warm the Space, etc.).
- [ ] `launch/posts/community-posts.md` — r/LLMDevs post, X thread,
      channel notes (incl. where NOT to put the demo link).
- [ ] `launch/outreach/OUTREACH.md` — DE + EN touch 1 and follow-ups 2–4,
      personalization slots, the written 2-week pilot success definition,
      the 20-min call script, tracking rules.
- [ ] `launch/outreach/targets.example.csv` — company-level scaffold
      seeded from MARKET.md §5; `targets.csv` gitignored.
- [ ] Gate green; eval byte-identical; no engine/eval change.

## Scope

**In:** the drafts above, the `.gitignore` line, `launch/README.md` link
fixes if needed.
**Out:** posting/sending anything; a blog/long-form benchmark post (the
report itself serves; write the post if HN demands it); email tooling or
CRM; any engine/docs-site change beyond `launch/`.

## Eval impact

None — drafts only. All six lines byte-identical.

## Risks / open questions

- Drafts age: the header convention (decision 3) puts re-verification on
  the send checklist rather than pretending CI can pin a thing meant to be
  hand-edited.
- The X thread's tone is deliberately more direct than the docs; the
  honesty constraints still bind (decision 4). If in doubt at send time,
  the maintainer cuts, not embellishes.
- No ADR — nothing hard to reverse; unsent drafts are free to change.
