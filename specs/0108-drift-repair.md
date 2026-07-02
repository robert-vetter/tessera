# 0108. Milestone 16 Unit 1: repair the audited documentation drift (D1–D7)

- **Phase / milestone:** Milestone 16 (Act 2 opener), Unit 1 — see spec 0107
  and [`docs/AUDIT_2026-07-02.md`](../docs/AUDIT_2026-07-02.md).
- **Issue:** —
- **Status:** implemented

## Problem

The audit found the docs lagging reality after the autonomous Milestone-15 run:
STATUS/CHANGELOG missing four merged PRs (D1), a now-false WRITEUP limitation
(D2), seven phantom spec numbers (D3), a DEPLOYMENT self-contradiction (D4), a
README milestone-count error (D5), CAPABILITIES items readable as built when
they are not (D6), and ~60 stale merged remote branches (D7). "State lives in
the repo" only works when the state is true.

## Acceptance criteria

- [x] STATUS gains a **backfilled, honestly-labeled** entry for the 2026-07-01
      M15 sessions (PRs #115–#117), reconstructed from the PRs + ADR 0026.
- [x] CHANGELOG `[Unreleased]` lists the three merged M15 units + the Act-2
      planning corpus; "*(nothing yet)*" removed.
- [x] WRITEUP: the "not idempotent … not engineering a dedup key" limitation
      rewritten to the ADR-0026 truth (best-effort idempotency engineered,
      residuals named); the "next posture steps" paragraph now says M15 is in
      flight and nothing has been sent.
- [x] DEPLOYMENT: the embeddings row says **built and measured on SAP**
      (M6–M7, ADR 0015–0017), not "deliberately not built".
- [x] README: "nine" → "ten" post-roadmap milestones; the MCP section carries
      the M15-in-flight wording (still: nothing sent); the Status section and
      repository map point at `ROADMAP2.md` / `MARKET.md` / `AUDIT_2026-07-02.md`.
- [x] CAPABILITIES: intro states the future-work convention; PDF/office +
      chat-transcript ingestion, incremental re-ingest, and conversational
      continuity are explicitly marked *(future work)*.
- [x] `specs/README.md` gains the numbering ledger (phantom 0050/0069/0071/
      0076/0104–0106; the 0075/0079 slug collision; M16 = 0107–0111 with M15's
      remainder under 0111).
- [x] ROADMAP2 reflects the corrected Z Fellows situation (applicant work-month,
      weekly ship-updates, check-in presentation, the public commitment to a
      live demo + first external users).
- [x] Stale, fully-merged remote branches pruned (verified merged into `main`
      before deletion; `main` and the active unit branch untouched).

## Scope

**In:** exactly the drift items above — docs and remote-branch hygiene.
**Out:** any code change (Units 2–3), the one-shot (Unit 4), CAPABILITIES
restructuring beyond status markers, rewriting history (backfill is labeled as
backfill; no dates are faked).

## Eval impact

None — docs only. Gate + eval run to prove the floors are untouched.

## Risks / open questions

- The backfilled STATUS entry must never read as contemporaneous — mitigated by
  the explicit honesty note naming when and from what it was reconstructed.
- Branch deletion is remote state, not PR-reviewable — mitigated by deleting
  only branches `git branch -r --merged origin/main` lists, and recording the
  action here and in STATUS.
