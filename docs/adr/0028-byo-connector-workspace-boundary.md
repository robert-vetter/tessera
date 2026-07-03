# 0028. BYO connect is fetch-to-local-workspace; answering stays offline

- **Status:** accepted
- **Date:** 2026-07-03

## Context

Milestone 18 (spec 0117) makes Tessera usable on repositories we do not own:
`tessera connect github <owner>/<repo>` must give a design partner grounded,
provenance-complete RCA over *their* CI failures. ADR 0014 solved the
adjacent problem for **our** repo with a run-once dev script and a
**committed** snapshot — but a foreign snapshot cannot be committed (it is
not ours to redistribute, it would bloat the repo, and it would stale), and
a pilot cannot depend on hand-editing pinned run ids in a script. Meanwhile
the constraints that made ADR 0014 right still bind: clone-and-run stays
offline and key-free, CI never touches the network, and answering must be
deterministic over its inputs.

Two measured facts shape the design (probed 2026-07-03, spec 0117): GitHub
serves run/job/PR *metadata* of public repos anonymously, but returns 403
for log *content* without a token — and the log endpoints answer with a 302
to signed blob storage, where a naive HTTP client would re-send the
`Authorization` header.

## Decision

**Fetch writes a gitignored local workspace; answering reads only that.**
`tessera connect github <owner>/<repo>` is the network moment: a bounded
fetch (recent runs, failed-run logs for the most recent failures, one page
of PRs — explicit caps, tunable by flags) normalized into the **exact
committed-snapshot format of ADR 0014** under `var/connect/<owner>-<repo>/`,
with a `MANIFEST.json` pinning what was fetched (run ids, snapshot date,
caps, scrub counts, named misses) and a `NOTICE` naming the upstream.
`tessera ask <owner>/<repo> "…"` builds the graph from those files alone —
the same `GitHubActionsSource`, parameterized by directory, zero engine
change — so answers are deterministic over the snapshot and work with the
network unplugged. The workspace is **never** committed: the committed proof
of generality is a report (numbers + reproduce commands in specs/STATUS),
not foreign fixtures.

**Auth is optional, minimal, and read-only.** Metadata fetches run
anonymously by default. The optional classic **no-scope** `GITHUB_TOKEN`
from the gitignored `.env` raises rate limits and unlocks failed-run logs;
without it, connect degrades honestly to a metadata-only snapshot and says
so. The connector never reads `TESSERA_GITHUB_TOKEN` (the actuator's RW
credential stays off every read path), never persists or echoes the token,
and follows log redirects manually so the auth header is sent to
`api.github.com` and nowhere else.

**Foreign text is scrubbed before it reaches disk.** Named content patterns
(GitHub/AWS/Slack token shapes, `Authorization:` header values, sensitive
`key=value` assignments) replace matches with a visible marker; counts land
in the manifest. What the caps or format divergence exclude is a **named
miss** in the manifest and the connect output — the ADR 0014
preserve-the-divergence posture extended: misses are recorded, never
papered over.

## Consequences

- **Easier:** a pilot is two commands on any public repo; clone-and-run, CI,
  and the six committed battery lines are untouched (no foreign data in the
  repo, no token in CI, no network at answer time).
- **Easier:** one snapshot format means one reader — the source module,
  locator kinds, RCA, verifier, and provenance rendering all apply to
  foreign repos with zero change; fixes benefit both corpora.
- **Accepted cost:** a workspace is a point-in-time copy that stales as the
  upstream repo moves; the manifest's pinned ids + snapshot date make that
  visible, and re-running `connect` replaces the snapshot atomically.
- **Accepted cost:** recorded BYO numbers are timestamped measurements over
  data that expires (GitHub log retention ~90 days) — reproducible same-day,
  historical afterwards; the "ran on X" pattern the project already uses.
- **Accepted cost:** without a token the snapshot has no logs, so RCA
  grounds on run metadata only — a stated degradation, not a hidden one.

## Alternatives considered

- **Commit foreign snapshots like ADR 0014.** Rejected: not ours to
  redistribute, unbounded repo growth, and instantly stale — and it would
  make the eval's committed corpus depend on someone else's CI.
- **Fetch live at answer time.** Rejected: breaks offline determinism and
  the key-free posture (the same reasons as ADR 0014, now with a token in
  the answer path — worse).
- **Require the token and always fetch logs.** Rejected: anonymous
  metadata-only mode is a real, honest pilot on rate-limited days, and
  "never required" is the posture the kickoff fixed.
- **Use the run-logs zip (one request per run).** Rejected: it bundles every
  job's logs — hundreds for a matrix project — where the per-job endpoint
  fetches only the ≤3 failed jobs the snapshot needs.
- **A connector plugin framework.** Rejected again (ADR 0014): two doors
  (`connect github`, `ingest <dir>`) still do not justify an abstraction.
