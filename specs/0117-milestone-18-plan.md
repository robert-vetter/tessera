# 0117. Milestone 18 plan: usable on your data

- **Phase / milestone:** Milestone 18 — Act 2's third milestone
  ([`docs/ROADMAP2.md`](../docs/ROADMAP2.md)): Tessera answers with full
  claim-level provenance on data we did **not** author — the design-partner
  pilot vehicle. Post `milestone-17` (the hosted demo is live).
- **Issue:** —
- **Status:** approved (autonomous mode; maintainer's kickoff 2026-07-03).

## Problem

Every measured corpus so far is one we authored (synthetic SALT/DevEx) or
snapshotted from our own repository (the ADR 0014 GitHub Actions connector).
A design partner's first question is "does it work on *my* data?" — and the
pilot offer (ROADMAP2 M18.3) depends on the answer being yes, demonstrated,
in under 30 minutes. M18 builds the two BYO doors (`tessera connect github`,
`tessera ingest <dir>`) and the runbook, **without touching the engine**: the
six committed battery lines stay byte-identical, the hosted demo / UI / MCP
surfaces keep working on the committed demo data, and clone-and-run stays
green with no foreign data present.

**Recorded decisions (autonomous mode):**

1. **Proof corpora** (kickoff (a); verified live 2026-07-03 by unauthenticated
   API probes). **Large: `astral-sh/uv`** — ~5,113 failed workflow runs total,
   most recent the same day (run 28641345176, "CI", 2026-07-03T05:51Z); a
   massive matrix-CI project, and the honest narrative fit that Tessera's own
   toolchain runs on it. **Small: `simonw/llm`** — 268 failed runs, most
   recent 2026-07-02 (run 28608226231, "Test"); a single-maintainer CLI
   project. The exact run ids fetched and the snapshot date are pinned in each
   workspace `MANIFEST.json` at fetch time and reported in STATUS; generality
   is claimed for **exactly these two** corpora, no further.
2. **Data posture** (kickoff (b)). Foreign snapshots live in a gitignored
   local workspace, `var/connect/<owner>-<repo>/`, and are **never
   committed** — foreign log text is not ours to relicense, and committed
   foreign fixtures would bloat and stale. Clone-and-run stays green without
   any foreign data. The committed proof is a **report**: numbers + reproduce
   commands in the unit specs and STATUS (the M6/M7 "ran on X, recorded"
   pattern). `var/` joins `.gitignore` in Unit 2.
3. **Auth posture** (kickoff (c)) — **amended by measurement.** Run/job/PR
   *metadata* fetches unauthenticated by default (measured: 200 anonymous).
   But GitHub requires authentication for log *content* even on public repos
   — measured 2026-07-03: anonymous `GET …/actions/runs/{id}/logs` and
   `…/jobs/{id}/logs` both 403 ("Must have admin rights" is GitHub's
   anonymous-caller message); the same calls with the maintainer's classic
   **no-scope** `GITHUB_TOKEN` return 200. So: the optional token from the
   gitignored `.env` raises rate limits (60/h → 5,000/h) **and unlocks
   failed-run logs**; without it, `connect` still works but grounds RCA on
   run/job metadata only, and says so plainly. Never required for metadata,
   never in CI, never at answer time — fetch is a dev-time action; answering
   reads only the local snapshot (ADR 0014 posture, extended by ADR 0028).
4. **One snapshot format, one reader.** The BYO fetcher normalizes GitHub
   REST responses into the **exact on-disk snapshot format** the committed
   `data/github_actions/` corpus already uses: `runs/<id>.json` (the gh-CLI
   field shape: `databaseId`, `workflowName`, trimmed `jobs`),
   `logs/<id>.failed.log` (the TSV `job⇥step⇥<timestamp> <message>` shape,
   synthesized from per-job logs + the jobs JSON's per-step timestamps), and
   `MANIFEST.json`. The existing `GitHubActionsSource(data_dir=…)` — already
   a parameterized dataclass — reads it **unchanged**; workspace graph/KB
   builders live in the new `tessera/connect/` package. Zero change to
   `sources/github_actions.py`, the engine, or any battery.
5. **CLI: a thin dispatcher; the business door unchanged.** The `tessera`
   entry point moves from `tessera.business.cli:main` to a new
   `tessera/cli.py` that dispatches on an exact first argument — `connect`,
   `ask`, `smoke`, `ingest` — and otherwise falls through to the business CLI
   with identical behaviour (its contract is a free-text question; the four
   reserved words are not natural questions). Recorded residual: a question
   whose first word is literally a reserved word needs `tessera-chat` or
   rephrasing. This delivers the promised UX (`tessera connect github
   <owner>/<repo>`, `tessera ask <owner>/<repo> "…"`, `tessera ingest <dir>`)
   with the business module untouched.
6. **Scrubbing at the fetch boundary.** Foreign text is scrubbed **before it
   reaches disk**: named content patterns (GitHub token prefixes `ghp_`/
   `gho_`/`ghu_`/`ghs_`/`ghr_`/`github_pat_`, AWS `AKIA…` keys, Slack `xox…`
   tokens, `Authorization: Bearer/token …` header values, and
   `key=value`-shaped assignments whose key matches the M15 sensitive-key
   vocabulary) — extending the M15 receipt posture (allow-listed JSON fields
   + key-based redaction) with content patterns for logs. Replacement is a
   visible `***SCRUBBED***` marker; per-snapshot scrub counts are reported
   and recorded in the manifest, never silent.
7. **Bounded fetch, named misses.** Defaults (tunable flags, recorded in the
   0118 spec): last 30 runs (all conclusions, one page), failed-run logs for
   at most the 5 most recent failed runs, at most 3 failed jobs per run,
   per-job log capped (tail-kept, cap recorded in the manifest when hit),
   jobs listing capped at 3 pages. Anything the caps exclude, and any log
   whose format defeats step attribution or signature extraction, is a
   **named miss** in the manifest / smoke report (ADR 0014's
   preserve-the-divergence posture) — papered over never.
8. **Units and reviews.** 0118 `connect github` + `ask` (trust-bearing →
   pre-merge adversarial multi-agent review; carries **ADR 0028**, the BYO
   connector boundary). 0119 per-repo smoke battery (reported, not CI-gated —
   foreign data is not committed). 0120 `ingest <dir>` (trust-bearing →
   adversarial review; carries **ADR 0029**, the declared ingest-config
   format). 0121 `docs/PILOT.md`. Close: STATUS wrap, CHANGELOG
   `[milestone-18]`, the ADR 0008 empty-diff frozen-core audit
   (`milestone-17..HEAD`; sanctioned deltas: **new files only** plus the one
   `pyproject.toml` entry-point line), tag `milestone-18`, M19 kickoff.

## Acceptance criteria

- [ ] **Unit 2 (spec 0118, ADR 0028):** `uv run tessera connect github
      <owner>/<repo>` fetches a bounded, scrubbed snapshot into
      `var/connect/<owner>-<repo>/`; `uv run tessera ask <owner>/<repo>
      "Why did run <id> fail?"` answers **offline** with full claim-level
      provenance via the existing RCA/routing; passed runs and unknown run
      ids refuse; rate-limit and no-token paths degrade honestly with plain
      messages. Adversarial review before merge.
- [ ] **Unit 3 (spec 0119):** `uv run tessera smoke <owner>/<repo>` derives
      and runs the per-repo checks (runs parse; ≥1 failed run grounds an RCA
      whose claims pass `is_supported`; provenance resolves end-to-end;
      refusals fire on a passed and an unknown run) and prints a report; run
      against **both** proof corpora with numbers recorded in the spec/STATUS.
- [ ] **Unit 4 (spec 0120, ADR 0029):** `uv run tessera ingest <dir>` ingests
      CSV + Markdown/plain text through the existing doors from a small
      declared config; `tessera ask <dir> "…"` answers with provenance;
      ambiguous names refuse; proven on a public-data corpus whose origin the
      spec records. Adversarial review before merge.
- [ ] **Unit 5 (spec 0121):** `docs/PILOT.md` (prerequisites, exact commands,
      what the client keeps, honest limits) in mkdocs nav with README/DEMO
      pointers; the <30-minutes-from-clone success criterion measured and
      recorded.
- [ ] **Close:** all six committed battery lines byte-identical; gate green
      every unit; frozen-core empty-diff audit clean; CHANGELOG; tag
      `milestone-18`; M19 kickoff handed back.

## Scope

**In:** the four build units + close, exactly as above. **Out:** any engine/
verifier/battery change; committing foreign data; any network at answer time;
connectors beyond GitHub Actions + local dir (no third connector, ROADMAP2
guard); auth beyond the optional no-scope env token; the M19 launch motion;
UI changes (the UI keeps serving the committed demo data).

## Eval impact

None on the six committed lines — proven at every unit's gate (business
11/53, devex 9/24, github_actions 5/8, all byte-identical). New BYO
measurements are **reported** (Unit 3's smoke battery + STATUS numbers), not
CI-gated, because their data is deliberately not committed; the honest
generality claim is scoped to the two proof corpora + one assembled dir
corpus.

## Risks / open questions

- **Foreign log volatility:** GitHub run logs expire (~90 days) and repos
  move; the recorded numbers are timestamped measurements (the "ran on X"
  pattern), and each workspace MANIFEST pins run ids + snapshot date so a
  same-day re-fetch reproduces the snapshot. After expiry the report stands;
  the commands still work against fresh runs.
- **Rate limits during development:** bounded fetch (~≤25 requests/snapshot)
  fits the anonymous 60/h budget; the maintainer's no-scope token covers
  iteration. CI never fetches.
- **Format divergence beyond the two corpora** (self-hosted runners, exotic
  workflows): explicitly unmeasured — the claim stays scoped; the smoke
  battery is exactly the tool a third repo runs first.
- **Dispatcher reserved words** (decision 5): a business question starting
  with `connect`/`ask`/`smoke`/`ingest` mis-routes — accepted, documented
  residual; `tessera-chat` covers it.
- **`var/` hygiene:** foreign data on disk but never in git — `.gitignore`
  entry + a `NOTICE` written into every workspace naming the upstream repo
  and that redistribution follows the upstream's terms.
