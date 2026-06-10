# 0041. The technical write-up

- **Phase / milestone:** Phase 4 — platform, polish, and the story (spec 0035 Unit 7)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

ROADMAP Phase 4: "a clear technical write-up / blog post: the problem, the
approach, the honest results (including limitations), and what was learned."
Everything it needs already exists in the repo — specs, ADRs, the append-only
eval history, the STATUS journal — but scattered. The write-up is the one
document a stranger reads first and a reviewer reads instead of the code.

## Acceptance criteria

- [ ] `docs/WRITEUP.md`, in the mkdocs nav, self-contained: the problem, the
      architecture (core + two verticals + measured trust), how faithfulness
      is defined and earned (adversarially tested, floor-gated), the **honest
      coverage trail** exactly as recorded (business 0.929 → 0.938 → 1.000;
      devex 0.917 → 1.000) with what each movement was, the two-vertical
      generality proof (empty frozen-core diff), the platform posture
      (designed for SAP, local-first), limitations stated plainly, and
      deliberately deferred future work.
- [ ] Every number traces to `eval/history.jsonl`; every decision cites its
      ADR; no claim the repo cannot back (the project's own rule, applied to
      its own story).
- [ ] Readable by a non-author in one sitting; the demo commands shown
      actually run.

## Scope

**In:** the write-up + nav. **Out:** README/index restructuring (Unit 8's
stranger pass); marketing language; any new capability.

## Eval impact

None (document only).

## Risks / open questions

- Overclaiming is the failure mode (CLAUDE.md guardrail) — mitigated by
  citing the recorded numbers verbatim and naming the misses and limits with
  the same prominence as the wins.
