# Pilot in a day

**The offer:** we instrument one of your agent use cases with **provenance** and
**action receipts** — every answer traces to its source, every action leaves a
record — and you keep the audit artifact. This runbook takes a stranger from a
clean clone to a grounded, provenance-complete answer **on their own data in
under 30 minutes**, offline, with no account and no data leaving the machine.

> **The agent can only say what it can prove — and only do what you approve.**
> Faithfulness is a number in CI, not a vibe.

---

## What you need (~5 minutes)

- **Python 3.12** and [`uv`](https://docs.astral.sh/uv/)
  (`curl -LsSf https://astral.sh/uv/install.sh | sh`), or Docker (see the
  README's container section).
- The repository:
  ```bash
  git clone https://github.com/robert-vetter/tessera && cd tessera
  uv sync
  ```
- **Optional**, only to fetch the failed-run *logs* of a public repo: a
  **classic GitHub token with no scopes** in a gitignored `.env`
  (`GITHUB_TOKEN=…`; mint one at
  <https://github.com/settings/tokens/new> with nothing checked). It raises
  rate limits and unlocks log content; it is never required, never sent
  anywhere but `api.github.com`, and never committed. Without it you still get
  run and PR metadata.

Confirm the install with the shipped batteries — every faithfulness number is
`1.000`:

```bash
uv run tessera-eval
```

---

## Path A — your CI failures (a public GitHub repo, ~10 minutes)

```bash
# 1) Snapshot a bounded, scrubbed slice of the repo's Actions history into
#    var/connect/ (gitignored — nothing about your repo is committed).
uv run tessera connect github <owner>/<repo>

# 2) `connect` prints a ready-to-run question with a real failed run id. Ask it —
#    this runs OFFLINE over the local snapshot; every claim cites a workspace file.
uv run tessera ask <owner>/<repo> "Why did run <run-id> fail?"

# 3) Check the trust contract actually holds on your data:
uv run tessera smoke <owner>/<repo>
```

`smoke` reports five checks — runs parse, a failed run grounds a root-cause
answer, every claim passes the same verifier the batteries use, provenance
resolves to real files, and refusals fire on a passed / unknown run — plus a
**warning** when a "recurring failure" rests only on a generic
`Process completed with exit code N` trailer (an honest weak-signal flag, not a
failure). If `smoke` reports a hard `FAIL` on your repo, that is the tool doing
its job: it tells you the contract has a gap on that data *before* you trust an
answer.

## Path B — your CSV + documents (~10 minutes)

Describe a directory of CSV tables and Markdown/text with a small
`tessera.toml` — the worked example is
[`data/ingest_demo/tessera.toml`](https://github.com/robert-vetter/tessera/blob/main/data/ingest_demo/tessera.toml),
and the format is [ADR 0029](adr/0029-declared-ingest-config.md):

```bash
uv run tessera ingest <your-dir>
uv run tessera ask <your-dir> "<a question naming a row or an entity>"
```

You get grounded, cited answers, multi-field entity resolution across your
tables, and an **honest refusal when a name is ambiguous** — two distinct
entities sharing a name are kept apart, never silently merged (as long as a
declared `match_field` distinguishes them). Try it first on the shipped
public-domain demo:

```bash
uv run tessera ingest data/ingest_demo
uv run tessera ask data/ingest_demo "What do you know about Santa Fe?"
uv run tessera ask data/ingest_demo "Tell me about Portland"   # → ambiguous, refused
```

---

## What you keep — the audit artifact

- **The snapshot / corpus** under `var/connect/<owner>-<repo>/` (or your ingest
  directory): the exact data every answer was grounded in, with a
  `MANIFEST.json` that pins what was fetched, what was **scrubbed** before it
  hit disk, and every **named miss** (what a cap or a format quirk left out —
  never silent).
- **The answers**, each with a per-claim provenance trail to a specific file and
  line/row — copy them into your own record; they resolve offline, forever.
- **The smoke report** — a one-page, per-repo statement of whether the trust
  contract held on your data.
- If you exercise the action flow (the web UI or the MCP `execute_action`
  tool), an **execution receipt** — what was proposed, approved, and done
  (simulated by default; the real path is behind your credentials and your
  approval).

---

## Honest limits

- **Snapshot, not a live tap.** Answers are deterministic over a point-in-time
  local copy; GitHub logs expire (~90 days). Re-run `connect` to refresh. This
  is the price of offline, reproducible determinism
  ([ADR 0014](adr/0014-real-connector-snapshot-boundary.md) /
  [ADR 0028](adr/0028-byo-connector-workspace-boundary.md)).
- **Foreign data stays local.** Your snapshots are gitignored and never
  committed. The project's committed proof that BYO works is a *report* (numbers
  and reproduce commands), measured on two public repos — `astral-sh/uv` (large)
  and `simonw/llm` (small), both smoke-clean. Generality is claimed for what was
  measured, not beyond it; `smoke` is exactly the tool for a third repo.
- **Recurrence is only as specific as the error line.** A "recurring failure"
  built on a generic `exit code N` trailer is a weak signal; `smoke` flags it,
  and a sharper signature (plus a fix for a rarer recurrence-anchor edge that
  `smoke` also catches) is planned work.
- **No LLM in the trust path.** An optional model may *narrate* answers into
  prose, but the verifier and the receipts are deterministic — the LLM never
  attests. Nothing here says "hallucination-free"; it says *here is the
  evidence, and here is the number.*

**Success criterion (measured):** a stranger reaches a grounded,
provenance-complete answer on their own repository in **under 30 minutes from
clone**. The mechanical `connect` + `ask` cycle on a fresh repo is ~20 seconds
(measured); the rest is `uv sync` and reading this page.
