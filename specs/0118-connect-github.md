# 0118. `tessera connect github <owner>/<repo>` — grounded RCA on a foreign repo

- **Phase / milestone:** Milestone 18 Unit 2 (spec 0117 decision 8) — the
  first BYO door: point Tessera at any public GitHub repository and answer
  "Why did run X fail?" with full claim-level provenance, offline, over a
  local snapshot. Carries **ADR 0028** (the BYO connector boundary).
- **Issue:** —
- **Status:** approved (autonomous mode; decisions below recorded, not asked).

## Problem

The ADR 0014 connector proves real CI data flows through the unchanged
engine — but only for *our* repository, via a committed snapshot and the
authenticated `gh` CLI. A design partner needs the same on *their* repo with
nothing but `uv sync`: fetch a bounded snapshot of recent runs and failed-run
logs, scrub it, land it in a gitignored workspace, and answer over it with
the same RCA/refusal/provenance contract the batteries measure. The engine,
the sources module, and the six committed battery lines must not move.

**Recorded decisions (beyond spec 0117 items 3–7):**

1. **Fetch normalizes to the committed-snapshot format** (spec 0117 item 4):
   `runs/<id>.json` in the gh-CLI field shape (`databaseId`, `workflowName`,
   `displayTitle`, `headBranch`, `headSha`, `event`, `conclusion`,
   `createdAt`, trimmed `jobs`), `logs/<id>.failed.log` in the TSV
   `job⇥step⇥<timestamp> <message>` shape. The TSV is synthesized from
   per-**job** log downloads: each failed step's lines are selected by the
   jobs JSON's per-step `started_at`/`completed_at` window (compared on the
   second-precision prefix, inclusive); a failed step with no usable window
   falls back to the whole job log with an empty step column **and a named
   miss in the manifest**.
2. **Per-job logs, not the run zip.** The run-logs zip endpoint downloads
   every job's logs (hundreds for a matrix project like uv); the per-job
   endpoint fetches only failed jobs. Both need the token (measured, spec
   0117 item 3); the per-job path is the bounded one.
3. **Redirects are followed manually, and the token never leaves
   `api.github.com`.** GitHub answers log requests with a 302 to signed blob
   storage; `urllib` would re-send the `Authorization` header to the
   redirect target. The fetcher disables automatic redirects for log
   downloads and requests the blob URL with **no** auth header. (Adversarial
   review checklist item.)
4. **Token = `GITHUB_TOKEN` only** (classic, no scopes, from the sourced
   `.env`). Deliberately **never** `TESSERA_GITHUB_TOKEN` — the actuator's
   RW credential must not ride along on read paths (least privilege; the
   separation `.env.example` already promises). The CLI reports token
   *presence* only; the value appears in no file, no manifest, no message.
5. **Fetch set and caps** (defaults; `--runs/--failed/--jobs-per-run` flags):
   one page of the 30 most recent runs (all conclusions); failed-run logs
   for at most the **5** most recent failed runs among them; at most **3**
   failed jobs per run; jobs listing capped at 3 pages (300 jobs); per-job
   log capped at 2 MiB (tail kept — errors live at the tail; cap noted in
   the manifest when hit). Failed runs beyond the log cap are **omitted from
   the snapshot entirely** and listed in the manifest as
   `omitted_failed_run_ids` — an `ask` about one refuses "no run X in the
   knowledge graph", which is true of the snapshot and visibly explained by
   the manifest + connect's own output. Recent **PRs** (one page of 30,
   title/state/author/dates + body capped at 500 chars, scrubbed) ingest as
   `PR:` rows for the lexical path — the "PRs if cheap" kickoff item, one
   request.
6. **Refresh = replace, atomically.** The snapshot builds in a temp dir
   beside the workspace and lands by rename; a failed fetch leaves any prior
   workspace untouched. Re-running `connect` replaces the snapshot and its
   manifest (the pinned run ids + snapshot date are the record of what is
   current).
7. **`ask` routes like the measured battery:** a question naming a run id
   (the existing `RUN_ID` pattern) → the unchanged `explain_failure` over
   the workspace graph; anything else → the engine's lexical lookup over the
   workspace KB (which refuses honestly on zero overlap). The route and its
   reason print like every other door; answers render with the standard
   claim-level provenance (`Answer.render`).
8. **New code lives in `tessera/connect/` + a thin `tessera/cli.py`
   dispatcher** (spec 0117 item 5). `pyproject.toml`'s `tessera` script is
   the only existing line that changes repo-wide. `var/` joins `.gitignore`;
   every workspace gets a `NOTICE` naming the upstream repo and that its
   text remains the upstream's (no redistribution).

## Acceptance criteria

- [ ] `uv run tessera connect github <owner>/<repo>` (with `GITHUB_TOKEN`
      present) writes `var/connect/<owner>-<repo>/{runs,logs,MANIFEST.json,
      NOTICE}`, prints what it fetched (runs, failed logs, PRs, scrub
      counts, misses, request count) and a copy-paste `ask` example naming a
      real failed run id.
- [ ] Without a token: metadata-only snapshot (runs + PRs, no logs), a plain
      statement of why logs are absent and how to add the optional no-scope
      token; exit 0 (a degraded snapshot is still a snapshot).
- [ ] `uv run tessera ask <owner>/<repo> "Why did run <failed-id> fail?"`
      answers **offline** with grounded claims (run row + error log spans,
      recurrence when a prior run shares the signature) — every claim
      carrying provenance to workspace files.
- [ ] Refusals: a passed run refuses ("did not fail"); an unknown/omitted
      run id refuses by name; an unconnected target says how to connect.
- [ ] Honest failure paths: 404 (missing/private repo), 403 rate-limit
      (names the reset time and the optional token), network errors — each a
      clean message and non-zero exit, no half-written workspace.
- [ ] Scrubbing: the named patterns (spec 0117 item 6) applied to log text,
      PR text, and run/job JSON string fields **before disk**; counts in the
      manifest; a test proves a planted token shape never reaches the
      workspace.
- [ ] The token is never written to any file or echoed; log-blob requests
      carry no auth header (tested with a fake transport asserting header
      absence on the redirect leg).
- [ ] All tests offline (fake transport); gate green; the six committed
      battery lines byte-identical; `sources/github_actions.py` and the
      engine unchanged (`git diff` clean over them).
- [ ] **Pre-merge adversarial multi-agent review** (trust-bearing: foreign
      attacker-shaped text enters the provenance path; a credential is
      handled) — findings fixed or explicitly accepted in the PR.
- [ ] Live proof recorded in the PR/STATUS: connect + ask against both spec
      0117 proof corpora (`astral-sh/uv`, `simonw/llm`), output excerpts +
      request counts + scrub counts (the committed proof is the report;
      the workspaces stay local, spec 0117 item 2).

## Scope

**In:** `tessera/connect/` (fetcher, scrubber, workspace builders, CLI),
`tessera/cli.py` dispatcher, pyproject entry-point line, `.gitignore` `var/`,
tests, ADR 0028, README pointer. **Out:** the smoke battery (Unit 3);
`ingest <dir>` (Unit 4); PILOT.md (Unit 5); any change to engine, sources,
verifier, batteries, UI, MCP; private repos; any write to GitHub; any
network at `ask` time.

## Eval impact

None — the six committed lines are untouched (proven at the gate). The BYO
path's own measurement arrives as Unit 3's reported smoke battery; this
unit's live proof is recorded output, not a gated number.

## Risks / open questions

- **Foreign text is attacker-shaped** (log lines and PR bodies flow into
  claims/rendering): mitigated by scrub-before-disk, verbatim-quote claims
  (the verifier checks containment, not meaning), and the adversarial
  review. The UI is out of scope — it renders committed demo data only.
- **Step-window attribution** can mis-slice when GitHub's step timestamps
  are coarse; the fallback (whole job log, named miss) keeps provenance
  truthful — the locator then names the job, not a step. Measured on both
  proof corpora: second-precision boundaries let neighbouring-step lines
  that share the boundary second ride into the window (post-job cleanup
  after the error line). Inclusive boundaries are the deliberate side of
  that trade — extra verbatim context over a lost error line.
- **Large-matrix repos** (uv): caps keep the fetch bounded; what the caps
  exclude is named. The smoke battery (Unit 3) is where "did the caps hide
  the interesting failure?" becomes visible per repo.
- **GitHub API drift** (field renames): the fetcher pins
  `X-GitHub-Api-Version: 2022-11-28`.
- **Recurrence signal strength (named limitation).** The unchanged DevEx RCA
  labels a shared error *signature* across runs a "Recurring failure"; the
  signature is the first `##[error]` line, which on real corpora is often the
  generic trailer `Process completed with exit code N.` (measured: both proof
  corpora). The emitted claim stays literally true and verifier-checked (the
  fragment does appear in every cited log), but a generic trailer is a *weak*
  recurrence signal — two unrelated failures that share an exit code get the
  same label. This is surfaced, not hidden: Unit 3's smoke battery flags a
  recurrence claim whose signature is a bare exit-code trailer, and PILOT.md
  states it as an honest limit. The real fix — teaching `_signature` to skip
  generic trailers when a specific error line exists — is **deferred named
  future work**: `devex/rca.py` is frozen for this milestone (the ADR 0008
  empty-diff audit), so it must be done in a later milestone openly, with the
  batteries re-run, not silently here.
- **Adversarial review (recorded):** three lenses (security, trust-honesty,
  correctness) pre-merge. Fixed in this PR: control-sequence neutralization of
  all foreign text at the fetch boundary; manifest miss strings + excluded
  values scrubbed (nothing written bypasses the scrubber); non-HTTP network
  errors → `ConnectError` (spec acceptance criterion); scrub patterns made
  line-local (`[ \t]`, never `\s`) so a `password:`-terminated line can't eat
  the next TSV job column; tab/newline stripped from job/step names; redirect
  scheme guard + minimal opener (no file/ftp/data handlers) + auth only on
  https api host; CLI flag bounds; non-JSON-200 tolerance; workspace
  collision + traversal guards; token-aware 401/403 log diagnosis;
  scrub-then-truncate PR bodies with a visible marker; `total_run_count`
  coverage; boundary-second over-label named per run; metadata-only reason
  distinguished; atomic move-aside swap. Explicitly deferred: the recurrence
  `_signature` refinement (frozen file, above).

## Live proof (recorded at implementation, 2026-07-03)

Both spec 0117 proof corpora, fetched with the maintainer's no-scope token
and answered **offline** (the workspaces stay local, per decision — this
report is the committed proof):

- **`simonw/llm`** (small): connect → 17 requests; 10 runs kept (5 failed
  with logs, 4 failed omitted beyond the cap, 16 excluded as not
  success/failure — all named); 30 PRs; scrub counts `{}`.
  `ask "Why did run 28608226231 fail?"` → grounded RCA: run row (failing
  step "Check if cog needs to be run" in job "test (ubuntu-latest, 3.14,
  4.0rc1)") + the isolated `##[error]Process completed with exit code 5.`
  log span, every claim with workspace provenance.
- **`astral-sh/uv`** (large): connect → 18 requests; 21 runs kept (4 failed
  with logs, 0 omitted, 9 excluded — named); 30 PRs; scrub counts `{}`.
  `ask "Why did run 28641345176 fail?"` → grounded RCA: run row (failing
  step "Cargo test" in job "test / cargo test on linux") + the
  `error: test run failed` / `##[error]Process completed with exit code
  100.` span, 3 claims cited to workspace files.
- Refusals verified live on uv: passed run 28521696669 → "did not fail — it
  passed"; unknown run 99999999999 → "no run … in the knowledge graph".
- Scrub counts are honestly zero on both corpora (nothing credential-shaped
  present); the mechanism is proven by the planted-token tests.

Reproduce: `uv run tessera connect github <owner>/<repo>` then the `ask`
lines above (fresh runs will differ — GitHub log retention ~90 days; the
manifest pins what this measurement saw).
