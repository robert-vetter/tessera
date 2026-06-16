# 0045. The first real connector: GitHub Actions ingestion

- **Phase / milestone:** Milestone 5 — Hardening (spec 0043, unit 3)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

Both synthetic batteries are saturated at 1.000 (ADR 0007 trigger 2), and both
prior coverage recoveries closed misses the project itself *planted*. The honest
way to make the eval able to fail again — and to answer "can it surface a miss
you did not author?" — is to ingest **real** data. The WRITEUP already *claims*
the synthetic corpora are "drop-in shaped" for real connectors; this unit turns
that claim into a demonstration.

The chosen connector is the project's **own GitHub Actions history** (decided in
spec 0043: real, free, legally unencumbered, self-demonstrating). The
reconnaissance confirmed it is a genuine source of un-planted difficulty: real
run logs are TAB-delimited `job⇥step⇥<ISO-timestamp> <message>` with a UTF-8 BOM,
ANSI codes, `##[group]`/`##[error]` markers, JS stack traces, and **no
`FailedJob` field** — nothing like the synthetic `ERROR <svc>:` shape.

## Acceptance criteria

- [ ] A run-once dev script `scripts/fetch_github_actions_snapshot.py` snapshots
      a **pinned** set of runs (3 failures with logs + 2 successes) into
      `data/github_actions/` (`runs/<id>.json`, `logs/<id>.failed.log`,
      `MANIFEST.json` with `synthetic: false`, `NOTICE`). It is the **only**
      network touchpoint, never imported at runtime or by the eval; re-running it
      reproduces byte-identical fixtures (pinned ids + constant `snapshot_date`).
- [ ] `tessera.sources.github_actions.GitHubActionsSource` ingests the committed
      snapshot through the **same `Ingester` door**, reusing the existing
      `table-row` (run) and `log-span` (failed-step log) locator kinds with
      **zero change to `grounding.py`/`ingestion.py`** (ADR 0002 cashed a 4th
      time).
- [ ] The source does the GitHub-specific normalization that belongs in a source:
      lift `job`/`step` into the locator, drop transport noise (BOM, ANSI,
      per-line timestamp), **keep the real message text verbatim** including
      `##[error]` and the real failure vocabulary. The failing step is *derived*
      (the step whose conclusion is `failure`).
- [ ] A **separate** `build_github_actions_graph()` (not unioned into the
      synthetic DevEx graph) so all eight existing recorded numbers stay
      byte-identical this unit.
- [ ] Tests pin: ingestion shape, snapshot-date origin, derived failing step,
      preserved `##[error]` divergence (and absence of the synthetic shape),
      cross-run recurrence fragment, determinism, and the `log_of` graph links.
- [ ] An ADR (0014) records the fetch-vs-ingest boundary and the decision to
      ingest the logs raw (preserve the divergence) rather than normalize them to
      look synthetic.

## Scope

**In:** the fetch script, the committed snapshot, the source, the separate graph
builder, the tests, the NOTICE, ADR 0014.

**Out:** any eval battery, gold/synthetic case, or answer-path/router change over
the real runs (that is spec 0046 — where the measured miss and its deterministic
close live); a second connector or any non-GitHub source; live fetching anywhere
on the gate/eval path; PR/issue/ticket data from the GitHub API (the Actions
run/log surface only — the multi-hop ticket/PR material stays the synthetic
corpus's job, spec 0047).

## Eval impact

**None this unit.** No battery consumes the real graph yet, so all eight recorded
numbers are unchanged (verified by the eval running in the gate). The connector
*ingests*; spec 0046 *measures*.

## Risks / open questions

- **Real-failure skew:** 33 of 34 real failures are the same Pages-deploy 404 and
  exactly one is a code/gate failure (ruff format). The snapshot uses real data
  to stress **format/vocabulary divergence**, not failure-cause breadth — the
  synthetic corpus stays the breadth source. Recorded in the NOTICE.
- **Coarse log chunking:** the Pages failed-log is one `(deploy, UNKNOWN STEP)`
  group → one large chunk. Faithful (the fragment is in the chunk) but coarse;
  finer `##[group]`-based chunking is possible future refinement, noted not done.
- **Secrets:** `gh` masks tokens (`***`); the logs were scanned for unmasked
  secrets before commit (none). The repo is private; SHAs/Request IDs are
  non-sensitive runner metadata.
- **Log retention:** GitHub expires Actions logs (~90 days); pinning + committing
  the snapshot once removes that risk (re-fetch later may find expired logs).
