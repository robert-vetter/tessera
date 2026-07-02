# 0107. Milestone 16 plan: close & clean (Act 2 opener)

- **Phase / milestone:** Milestone 16 — the first milestone of Act 2
  ([`docs/ROADMAP2.md`](../docs/ROADMAP2.md)): repair the drift and fix the
  trust-path findings recorded in the 2026-07-02 audit
  ([`docs/AUDIT_2026-07-02.md`](../docs/AUDIT_2026-07-02.md)), then put the
  Milestone-15 one-shot within one safe maintainer command. Post-roadmap
  (`phase-0`…`phase-4`, `milestone-5`…`milestone-14`; M15 in flight).
- **Issue:** —
- **Status:** approved (autonomous mode, spec 0018: decisions recorded here.
  The maintainer directed the milestone start on 2026-07-02 — "begin M16 and
  prepare everything for the one-shot so I can execute it without problems" —
  and supplied the GitHub username `robert-vetter` for the sandbox repo.)

## Problem

The audit found the project *works exactly as documented* but carries (a)
documentation drift from the autonomous run (D1–D7: STATUS/CHANGELOG lag the
four merged M15 PRs; a now-false WRITEUP limitation; a DEPLOYMENT
self-contradiction; seven phantom spec numbers; stale branches), and (b) eight
code findings (B1–B8), the serious ones in the M15 real-execution path — two of
which (B1 recorder clobber, B2 label-dependent idempotency) directly endanger
the M15 one-shot's artifact and safety. M15's remaining units (the real send +
close) must not run until those are fixed. M16 is the audit acted on.

**Recorded decisions (not project-shaping — decided here per autonomous mode):**

1. **Spec numbering is reconciled forward-only.** The seven phantom numbers
   (0050, 0069, 0071, 0076, 0104–0106) are documented in a `specs/README.md`
   ledger, not backfilled as fabricated files. Spec 0103's internal reservation
   of 0106/0107 for M15's Units 4–5 is superseded: M16 takes 0107–0111; M15's
   real send + close execute under spec 0111's checklist.
2. **Recorder persistence policy (B1).** The recorder refuses to run an
   approved attempt when a receipt already exists on disk (checked *before any
   network*), persists only consummated outcomes (`created`/`exists`), and
   prints — but does not persist — an approved attempt that ends `error`, so a
   failed attempt never blocks or overwrites the historic artifact.
3. **Idempotency pre-check drops the label filter from the correctness path
   (B2).** The issues pre-check scans the unfiltered `state=all` listing for
   the exact body marker (same pagination + refuse-on-cap), making the check
   label-independent; the `idem-` label remains embedded as a visible,
   non-load-bearing handle. ADR 0026 gets an addendum (mechanism change + the
   marker-spoof residual).
4. **Verifier changes are transparent, never flattering (B6/B7).** Claims on
   refuse-kind cases are now faithfulness-scored (numbers proven unchanged on
   current data); over-citation and cross-boundary containment are *named* in
   an ADR 0005 addendum and pinned by a committed specimen test — reported
   honestly, not silently "fixed" into the gated metric.
5. **The sandbox repo is public** (`robert-vetter/tessera-exec-oneshot`), so
   the one real issue the receipt points at is publicly verifiable. Created by
   the agent (reversible); the PAT is minted by the maintainer only.
6. **M16 tags `milestone-16` only at its close, which includes M15's close** —
   if the maintainer defers the one-shot, M16 stays open. One unit, one PR,
   one spec, as always; the B-fixes carry the mandated pre-merge adversarial
   review (side-effect-capable surface).

## Acceptance criteria

- [ ] **Unit 1 — drift repair (spec 0108, docs only).** STATUS backfill for the
      0104–0106 sessions (honestly labeled as a backfill, reconstructed from
      PRs #115–#117); CHANGELOG `[Unreleased]` lists the three merged M15
      units; WRITEUP idempotency limitation rewritten to match ADR 0026;
      DEPLOYMENT embeddings row corrected; README "nine"→"ten" + Act 2
      pointer + M15-in-flight wording; CAPABILITIES gains status markers for
      unbuilt items; `specs/README.md` numbering ledger; ROADMAP2's Z Fellows
      framing corrected (applicant work-month with weekly updates + check-in
      presentation, publicly committed to a live demo + first external users);
      stale merged remote branches pruned.
- [ ] **Unit 2 — trust-path fixes B1–B5 (spec 0109).** B1 recorder
      never-clobber policy (decision 2, logic moved into the tested
      `agent/recording.py`); B2 label-independent pre-check (decision 3) + ADR
      0026 addendum; B3 `token` excluded from `repr`; B4 dynamic fence lengths
      neutralize fence injection (byte-reconstructability preserved); B5
      `{pr}` segment allowlist. Each pinned by a regression test; **pre-merge
      adversarial multi-agent review**; gate green; no battery number moves.
- [ ] **Unit 3 — verifier honesty B6/B7 (spec 0110).** Refuse-kind claims
      scored (decision 4, measured no-change proven); ADR 0005 addendum names
      over-citation + cross-boundary containment + the retired refusal blind
      spot; over-citation specimen test committed alongside the existing
      trigger specimens.
- [ ] **Unit 4 — one-shot preparation (spec 0111).** Public sandbox repo
      exists with an explanatory README; `.env` carries
      `TESSERA_EXEC_OWNER`/`TESSERA_EXEC_REPO` (non-secrets) + a commented
      PAT placeholder; DEPLOYMENT runbook updated for the new recorder
      behavior with the exact fine-grained-PAT recipe and the maintainer's
      two-command sequence (rehearsal → approved send); spec 0111 records the
      M15 close checklist (commit scrubbed receipt → STATUS/WRITEUP/README/
      CHANGELOG → empty-diff audit `milestone-14..HEAD` → tag `milestone-15`).
- [ ] **Wrap.** STATUS entry for this session; gate green throughout;
      faithfulness floors unchanged at 1.0.

## Scope

**In:** exactly the audit's D1–D7 and B1–B8 (B8 documentation-only note), plus
one-shot preparation. **Out:** everything else in Act 2 — the M17 UI/narration
work, M18 BYO connectors, M19 launch assets; any frozen-core change (none
anticipated; a necessary one gets its own ADR + review); the real send itself
(maintainer-only); new eval metrics (the over-citation measure is a committed
*specimen*, not a battery change).

## Eval impact

None intended: faithfulness stays gated at 1.0 and every battery number must be
byte-identical (proven at each unit's gate). Unit 3 extends *which claims are
accounted* (refuse-kind) with a measured no-change on current data — a
transparency fix, not a number change.

## Risks / open questions

- The B2 unfiltered scan reads more pages on a busy repo (cap → honest
  `inconclusive`); irrelevant for the empty sandbox, documented in ADR 0026.
- The B4 dynamic fence changes rendered bytes for values containing backtick
  runs (none exist in current data — proven by the byte-identical battery
  numbers and the payload boundary test).
- STATUS backfill must not pretend contemporaneity — entries are explicitly
  marked as reconstructed.
- The one-shot still depends on the maintainer minting the PAT; everything
  else is prepared so the send is two commands.
