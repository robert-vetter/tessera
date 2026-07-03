# 0119. Per-repo smoke battery — the floor for a connected repo

- **Phase / milestone:** Milestone 18 Unit 3 (spec 0117 decision 8). A
  connected repo has no gold set — its data is foreign and uncommitted — so
  the honest floor is an **auto-derived** self-check: does the trust contract
  actually hold on *this* snapshot? Reported, never CI-gated (foreign data is
  not committed, ADR 0028 / spec 0117 decision 2).
- **Issue:** —
- **Status:** approved (autonomous mode).

## Problem

`tessera connect github` (spec 0118) answers over data we did not author, but
the eval batteries measure only the committed corpora. A design partner needs
a per-repo answer to "does grounding actually work on my repo, or did the
snapshot come out empty/malformed?" — before trusting a single answer. The
smoke battery derives that check from the snapshot itself and prints a
pass/fail report: it is the BYO analogue of the gold set, scoped to what can
be asserted without hand-authored expectations.

**Recorded decisions:**

1. **Derived, not authored.** The checks are computed from the workspace: pick
   the most recent failed run *with a log*, the most recent passed run, and a
   run id absent from the graph. No per-repo gold file exists or is needed.
2. **The five checks** (each pass/fail with a one-line reason):
   - **runs-parse** — the snapshot ingests and yields ≥1 run row.
   - **failed-run-grounds** — a failed run with a log produces a grounded RCA
     with ≥1 claim (or `skip` if the snapshot is metadata-only — honest, not a
     failure).
   - **claims-supported** — every claim of that RCA passes the eval's own
     `is_supported` (the exact verifier the batteries use).
   - **provenance-resolves** — every cited origin resolves to a file that
     exists in the workspace (Pillar 1, end to end).
   - **refusals-fire** — a passed run refuses ("did not fail") and an unknown
     run id refuses by name; both must refuse.
3. **A named-caveat check, not a hard fail: recurrence-signal.** If the RCA
   emits a "Recurring failure" claim whose signature is a bare
   `Process completed with exit code N.` trailer (the spec 0118 named
   limitation), the report **warns** — the claim is true and verifier-passed,
   but the recurrence label is weak. A warning, not a failure: the trust
   contract (provenance) holds; the interpretation is soft. This is the
   surfacing the 0118 review asked for.
4. **Reported, not gated.** `tessera smoke <owner>/<repo>` prints the report
   and exits 0 when all hard checks pass, 1 otherwise — a developer signal,
   never part of `scripts/gate.sh` (which stays offline over committed data).
   The unit's own tests run on a **synthetic committed fixture workspace**
   (built in the test, not fetched) so the battery's logic is CI-covered
   without any foreign data.
5. **Run on both proof corpora, numbers recorded** (spec 0117 decision 8) in
   this spec and STATUS — the committed proof that the BYO path grounds on
   real foreign data.

## Acceptance criteria

- [ ] `uv run tessera smoke <owner>/<repo>` runs the five checks over the
      connected workspace and prints a labelled pass/fail/skip/warn report;
      exit 0 iff every hard check passes.
- [ ] `claims-supported` uses `tessera.eval.metrics.is_supported` unchanged
      (the battery verifier); `provenance-resolves` checks real files on disk.
- [ ] The recurrence-signal caveat warns (not fails) on a bare exit-code
      trailer signature.
- [ ] Unit tests build a synthetic workspace fixture and assert: a healthy
      snapshot passes all checks; a metadata-only snapshot skips
      failed-run-grounds honestly; a snapshot with only passed runs is caught;
      the recurrence warning fires on a trailer signature. All offline; gate
      green; six committed battery lines byte-identical; engine diff clean.
- [ ] Live: run on `astral-sh/uv` and `simonw/llm`; record the reports
      (numbers) in this spec and STATUS.

## Scope

**In:** `tessera/connect/smoke.py`, the `smoke` subcommand wiring, tests, this
spec, STATUS numbers. **Out:** any change to the verifier/engine/RCA; CI
gating on foreign data; a per-repo gold set; `ingest <dir>` (Unit 4).

## Eval impact

None on the committed lines (proven at the gate). The smoke battery is a
per-repo *reported* measurement, deliberately outside CI.

## Live proof (recorded at implementation, 2026-07-03)

Both proof corpora, connected and smoke-run offline:

- **`simonw/llm`** — runs-parse PASS (10 rows); failed-run-grounds PASS (run
  28608226231 → 3 claims); claims-supported PASS (3/3 via `is_supported`);
  provenance-resolves PASS; **recurrence-signal WARN** (its five cog-check
  failures share the `exit code 5` trailer — the caveat firing exactly where
  the weak signal is); refusals-fire PASS (passed run 27921952681 + unknown
  id). **All hard checks passed.**
- **`astral-sh/uv`** — runs-parse PASS (21 rows); failed-run-grounds PASS (run
  28641345176 → 3 claims); claims-supported PASS (3/3); provenance-resolves
  PASS; no recurrence warning (its failures do not share a trailer signature);
  refusals-fire PASS (passed run 28521696669 + unknown id). **All hard checks
  passed.**

The BYO trust contract — grounded, verifier-passed, provenance-complete
answers with honest refusals — holds on both foreign repos; the one known soft
spot is surfaced, not hidden. Reproduce: `uv run tessera connect github
<owner>/<repo>` then `uv run tessera smoke <owner>/<repo>`.

## Risks / open questions

- A smoke battery that passes when it shouldn't is worse than none — hence it
  reuses the exact `is_supported` verifier and checks real files, and its
  logic is CI-tested on a synthetic fixture workspace (the foreign data stays
  out).
- Metadata-only snapshots (no token) legitimately can't run
  failed-run-grounds; that is a `skip`, reported as such, not a pass or a
  fail — honesty over a green checkmark.
