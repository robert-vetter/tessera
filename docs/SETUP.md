# Setup — From docs to a running project

This is the step-by-step playbook for turning this folder of markdown into a real, running, properly-gated project. The guiding constraint: **nothing reaches `main` unverified.** That guarantee is enforced by machinery (branch protection + CI + pre-commit), not by willpower.

The work splits into three stages:
- **Stage A — manual, one-time.** Things only a human can do (accounts, tools, repo, protections).
- **Stage B — bootstrap the scaffolding with Claude Code.** Build the tooling skeleton *as the first units of work*, through the normal loop.
- **Stage C — the steady rhythm.** How every feature gets built for the next four months.

A principle that runs through all of it: **you don't tell Claude Code "build the whole thing."** You drive it one verified unit at a time, starting with the scaffolding itself. The docs already describe the destination; the loop gets you there safely.

---

## Stage A — Manual one-time setup

### A1. Install the toolchain (your machine)
Install, in roughly this order:
- **git** and the **GitHub CLI** (`gh`).
- **Node.js** (current LTS) — required by Claude Code.
- **Claude Code** (the npm package) — authenticate it.
- **uv** (Python environment/deps), **pnpm** (JS deps).
- **Docker** (for the reproducible dev container later).
- **pre-commit** (local commit gates).

You do not need to install ruff/mypy/pytest/eslint globally — uv and pnpm will manage those per-project once the config files exist.

### A2. Create the repository
- Create a **private** GitHub repo (keep it private until it's polished; flip to public near application time).
- Clone it locally.
- Copy the entire contents of this `tessera/` folder into the clone, **preserving the structure** (`README.md` and `CLAUDE.md` at the root; `docs/`, `.claude/`, `specs/` as-is).
- First commit — the docs are the foundation:
  ```
  git add .
  git commit -m "chore: project scaffolding and design docs"
  git push
  ```
- Create **GitHub milestones**, one per roadmap phase (Phase 0 … Phase 4).

### A3. Turn on the "nothing unverified" guarantee
This is the concrete answer to "I can't afford for things to get pushed without verification":
- In the repo settings, enable **branch protection on `main`**: require a pull request, and require **status checks (CI) to pass before merging**. (CI itself is created in Stage B; once it exists, require it here.)
- Work on branches, open PRs, let CI run, merge only when green. Even solo, this is the discipline that makes the history trustworthy.

### A4. Point Claude Code at the project
- Open Claude Code in the repo root. It reads `CLAUDE.md` automatically and picks up the `.claude/commands/` and `.claude/settings.json`.
- Connect MCP servers it will use:
  - a **GitHub** server, so Claude Code can manage issues/PRs/milestones from inside a session;
  - later, a **database** server for the data layer (added when Phase 1 needs it).
- Sanity check: ask Claude Code to list the available custom commands and confirm it can see `/spec`, `/plan`, `/verify`, etc.

> *Note on command format:* the `.claude/commands/*.md` files work as-is. If you want the current recommended form, move each into `.claude/skills/<name>/SKILL.md` with the same frontmatter — optional, both work.

---

## Stage B — Bootstrap the scaffolding with Claude Code

The repo has docs but no code and no tooling yet. The first units of work **are** the tooling. Treat them exactly like features: run them through the loop, and don't move on until each is verified.

### B1. Orient the agent
Start a session with a kickoff prompt along these lines:

> "Read `CLAUDE.md`, every file in `docs/`, and `docs/STATUS.md`. Summarize the project, the principles, and what Phase 0 in `docs/ROADMAP.md` requires. Do not write any code yet — confirm your understanding and propose the Phase 0 work as a short list of units, each of which we'll take through `/spec` → `/plan` → `/verify` → `/commit`."

This forces shared context before anything is built, and surfaces misunderstandings while they're cheap.

### B2. Build the tooling skeleton (Phase 0), one unit at a time
Drive Claude Code to produce these as separate, verified commits. Each is a `/spec` → `/plan` → implement → `/verify` → `/commit` cycle:

- **Python project config** — `pyproject.toml` wired for **uv**, with **ruff** (lint+format), **mypy** (types), **pytest** (tests).
- **Frontend project config** — `pnpm` workspace with **ESLint**, **Prettier**, **TypeScript strict**, **Vitest** (only when the conversational surface starts; can be deferred).
- **Pre-commit** — `.pre-commit-config.yaml` running formatters, linters, and a secret-scanner. Then run `pre-commit install` (manual, one line) so local commits are gated.
- **CI** — a `.github/workflows/` pipeline that runs format → lint → type-check → tests → (later) eval, on every PR. **Once this exists, go back to A3 and require it in branch protection.**
- **Reproducibility** — a `Dockerfile` and devcontainer so the project runs identically anywhere.
- **Docs site** — MkDocs Material config that publishes `docs/` to GitHub Pages.
- **Housekeeping** — `CHANGELOG`, issue/PR templates, README badges (CI, coverage, and the eval/faithfulness badge once the harness exists).

### B3. Prove the skeleton end-to-end
Before any real feature, confirm the machinery actually works on an empty project:
- `/verify` runs and is GREEN (even with near-zero code).
- A trivial PR triggers CI, CI passes, and branch protection blocks merging until it does.
- The "hello world" of the conversational surface from Phase 0 answers one hardcoded grounded question end-to-end.

When this is true, the scaffolding is real — and from here on, every feature lands on rails.

### B4. Close the session
Run `/wrap` so `docs/STATUS.md` records what was built and what's next. Always end sessions this way.

---

## Stage C — The steady rhythm (the next ~4 months)

From now on, every piece of the system — ingestion, the graph, grounded reasoning, the eval harness, the two verticals — is built the same way:

1. Pick the next unit from the current roadmap phase / milestone.
2. `/spec` — write the spec (turn it into a GitHub issue in the right milestone).
3. `/plan` — review and approve the plan (plan mode).
4. Implement on a branch (test-first where it fits).
5. `/verify` — green or it doesn't proceed.
6. `/document` — update docs / CHANGELOG.
7. `/commit` → open a PR → CI green → merge.
8. `/wrap` at session end.

Plus the periodic habits: `/adr` whenever a hard-to-reverse decision is made, `/audit` about weekly, and a **tagged release at the end of each phase** so the roadmap becomes visible, dated milestones in git.

### What you do vs. what Claude Code does
- **You (human):** install tools; create the repo and milestones; set branch protection; connect MCP servers; **approve plans; review and actually understand every PR before merging; make the architectural calls.** It is your project and your interview — you must be able to explain any line of it.
- **Claude Code:** generate config and scaffolding; write code, tests, and eval cases; implement features against approved plans; update docs; draft commits and PRs.

The division matters for one reason beyond quality: a reviewer at SAP will ask you how it works. The loop is designed so that you stay in the architect's seat throughout, not so that you hand the wheel to the agent.

---

## The one-line summary
Docs define the destination. Stage A builds the guardrails. Stage B builds the scaffolding through the loop. Stage C builds the system through the same loop, one verified, reviewed, merged unit at a time — for four months — until `main` is something a senior engineer can clone, run, and respect.
