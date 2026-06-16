# 0014. A real connector is fetch-to-committed-snapshot; logs ingest raw

- **Status:** accepted
- **Date:** 2026-06-16

## Context

Milestone 5 adds the project's first **real** data source — the repo's own GitHub
Actions history (spec 0045) — to break the all-1.000 saturation with un-planted
difficulty. A real connector pulls against two hard constraints the project has
held since Phase 0:

1. **Clone-and-run, offline, key-free.** `uv sync` → every door runs with no
   network and no token; CI resolves the locked env and never reaches out (a
   core claim, verified each phase).
2. **Determinism end to end.** No network/RNG/wall-clock in the trust path, so
   the eval reproduces on any machine (ADR 0003/0006).

A live API call inside ingestion or the eval would break both. Separately, there
is a design choice about *fidelity*: real GitHub logs look nothing like the
synthetic ones (`##[error]` vs `ERROR <svc>:`, nanosecond timestamps, ANSI, TAB
prefixes, no `FailedJob` field). We could normalize them at ingest to resemble
the synthetic shape (so the existing RCA heuristics "just work"), or ingest them
raw and let the divergence be measured.

## Decision

**Fetch is a run-once dev script; ingestion reads a committed snapshot.**
`scripts/fetch_github_actions_snapshot.py` is the **only** module that touches the
network. It pins explicit run ids (never "latest N"), carries a constant
`snapshot_date`, and writes `data/github_actions/` (`runs/<id>.json`,
`logs/<id>.failed.log`, `MANIFEST.json` with `synthetic: false`, `NOTICE`). The
runs are immutable history, so re-running reproduces byte-identical fixtures.
`tessera.sources.github_actions.GitHubActionsSource` reads only those committed
files — never `gh`, never the network — exactly as
`scripts/generate_salt_synthetic.py` sits outside the runtime/eval path while its
committed output is the dataset. The gate and the eval stay offline and key-free.

**Ingest the logs raw — preserve the divergence.** The source does the
GitHub-specific normalization that belongs in a *source*, not the engine: it
lifts `job`/`step` into the locator and drops transport noise (BOM, ANSI, the
per-line timestamp). But it **keeps the message text verbatim**, including the
`##[error]` marker and the real failure vocabulary, and **derives** the failing
step (the step whose conclusion is `failure`) since there is no `FailedJob`
field. We deliberately do **not** rewrite `##[error]` into the synthetic
`ERROR <svc>:` shape. The reuse of the existing `table-row`/`log-span` locator
kinds with zero engine change (ADR 0002 cashed a fourth time) is what proves the
ingestion door generalizes; the preserved divergence is what lets the next unit
measure an un-planted miss (spec 0046).

The real runs build a **separate** graph (`build_github_actions_graph`), not a
union into the synthetic DevEx graph — so the synthetic battery's numbers stay
byte-identical and the real-data measurements are isolated in their own battery.

## Consequences

- **Easier:** the clone-and-run / offline / deterministic guarantees survive a
  real connector untouched; CI needs no token; the snapshot is auditable like any
  committed fixture.
- **Easier:** because the logs are raw, the saturated eval gains a genuine,
  un-planted miss to measure (the RCA error-detector keys on `ERROR`, which real
  `##[error]` logs lack) — the whole point of the milestone.
- **Accepted cost:** the snapshot is a point-in-time copy that can drift from live
  CI; refreshing it is a manual, reviewed `fetch` run, not automatic. This is the
  same trade the SALT-synthetic generator makes and is the honest one for a
  reproducible eval.
- **Accepted cost:** real CI failures here are skewed (one dominant infra cause),
  so the real corpus stresses format/vocabulary divergence, not failure-cause
  breadth; the synthetic corpus stays the breadth source.

## Alternatives considered

- **Fetch live at ingest/eval time.** Rejected: breaks offline/key-free CI and
  determinism — the project's core reproducibility claim. A token in the gate is
  exactly what the local mode exists to avoid.
- **Normalize real logs into the synthetic `ERROR <svc>:` shape at ingest.**
  Rejected: it would hide the divergence and hand the eval a tautological pass —
  the connector would "work" precisely because we erased what makes real data
  hard. Preserving the divergence is the deliverable.
- **Union the real runs into the synthetic DevEx graph.** Rejected for now: it
  would perturb the eight pinned numbers and entangle the isolated real-data
  measurement with the synthetic battery. A separate graph keeps both honest; a
  union can come later if a cross-corpus question ever needs it.
- **A general-purpose connector framework (pluggable fetchers, credentials).**
  Rejected as premature: one real source does not justify an abstraction; the
  single `Ingester` Protocol already expresses everything needed (principle 5).
