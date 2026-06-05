# Engineering Handbook — Tessera

This is the **operating manual** for the project: how work flows, what tools enforce quality, how the repository stays organized over months, and how Claude Code is driven so the result reads as a senior-run software project rather than a pile of AI-generated files.

The rule behind everything here: **a reviewer who skims this repo should conclude, without being told, that a disciplined engineer ran it.** That impression comes from green checks, clean history, honest docs, and visible decisions — not from ceremony for its own sake.

> **Right-sizing note.** Real senior engineers are impressed by *appropriate* process, not maximal process. Everything below earns its place by either (a) keeping the project from drifting, (b) making quality measurable, or (c) making the work legible to a stranger. If a practice ever stops doing one of those three things, drop it.

---

## 1. The development loop

Every unit of work — a feature, a fix, a refactor — flows through the same seven steps. The Claude Code commands in `.claude/commands/` (documented in §5) encode this so it is one keystroke per step, not a remembered ritual.

```
/spec  →  /plan  →  implement  →  /verify  →  /document  →  /commit  →  /wrap
```

1. **`/spec` — define before building.** Write a short spec into `specs/` first: the problem, acceptance criteria, scope (in/out), and expected effect on the eval metrics. No code yet. This is where scope creep dies.
2. **`/plan` — plan before coding.** Turn the spec into an implementation plan (use Claude Code's plan mode). Read it, push back on it, approve it. Still no code.
3. **Implement.** Now the code gets written, test-first wherever it makes sense. The plan is the contract.
4. **`/verify` — the gate.** Format, lint, type-check, unit tests, and the **eval harness** all run and must be green. A change that lowers faithfulness without a documented reason does not pass.
5. **`/document` — keep docs true.** Update affected docs, the `CHANGELOG`, and any decision records. Documentation that lies is worse than none.
6. **`/commit` — small, honest commits.** Conventional Commits, scoped to one logical change, with a message that explains *why*, not just *what*.
7. **`/wrap` — end the session cleanly.** Update `docs/STATUS.md` with what was done, what's next, and any open questions. This is the single most important anti-drift habit: the next session starts from a written state, not from memory.

A non-trivial design decision triggers **`/adr`** at any point (see §6). A weekly **`/audit`** checks the whole repo for drift (see §7).

## 2. Branching and history

- **Trunk-based with short-lived branches.** `main` is always green and always demoable. Each unit of work gets a branch (`feat/…`, `fix/…`, `docs/…`, `eval/…`), opened as a PR even though you are solo — the PR is where CI runs and where the change is reviewable later.
- **Conventional Commits.** `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `eval:`. This makes the history readable and lets a changelog be generated automatically.
- **Tag a release at the end of each roadmap phase** (`v0.1.0` after Phase 1, etc.). Tagged phases turn the `ROADMAP.md` plan into visible, dated milestones in git — exactly the honest "I worked on this steadily for months" signal.
- **Never force-push `main`.** History is evidence; keep it intact.

## 3. The toolchain (the "additional software")

Chosen so the project is reproducible, enforceable, and presentable. Everything here runs both locally (via `/verify` and pre-commit) and in CI.

**Source & collaboration**
- **Git + GitHub** — issues, a Projects board (kanban), and **milestones mapped one-to-one onto the roadmap phases**. Every spec becomes an issue; every issue lives in a milestone.
- **Issue / PR templates** — so even solo work is filed consistently.

**Continuous integration — GitHub Actions** (the single most important "this is serious" signal)
- On every PR: format check → lint → type-check → unit tests → **eval regression** → docs build.
- A failing gate blocks merge. The green check on every commit is what a reviewer sees first.
- Publishes the docs site and updates the badges (below) on merge to `main`.

**Local quality gates**
- **pre-commit framework** — runs formatters, linters, and a secret-scanner before any commit even reaches CI, so `main` is protected by default.

**Python side**
- **uv** — environment and dependency management (fast, lockfile-based, reproducible).
- **ruff** — linting and formatting in one.
- **mypy** (or pyright) — static typing; the codebase is typed.
- **pytest** — unit tests; the **eval harness is a first-class test target**, not a side script.

**Frontend / TypeScript side (conversational surface)**
- **pnpm** — dependencies. **ESLint + Prettier** — lint/format. **tsc strict** — typing. **Vitest** — tests.

**Reproducibility**
- **Dockerfile + devcontainer** — anyone (including a reviewer) can clone and run the current state with one command. "It works on my machine" is not a defense.

**Documentation as a product**
- **MkDocs Material** (or Docusaurus) — turns `docs/` into a clean, browsable site deployed via GitHub Pages. This is the "strahlt nach außen" piece: a polished docs site signals professionalism before anyone reads a line of code.

**Visible health (README badges)**
- CI status, test coverage, and a **faithfulness/eval badge**. A green eval badge that says "trust is measured here" is a differentiator almost no portfolio project has.

**Changelog & versioning**
- **Conventional Commits → automated `CHANGELOG`** (e.g. git-cliff or release-please) + semantic version tags per phase.

## 4. How Claude Code is driven

Claude Code is the implementer; the discipline lives in configuration so the project cannot quietly drift.

- **`CLAUDE.md` is the constitution.** It is read at the start of every session and anchors conventions and principles so they never have to be re-explained. Keep it current; when a rule changes, change it here.
- **Custom commands** (`.claude/commands/`, §5) encode the development loop so each step is `/spec`, `/plan`, etc. — repeatable, not improvised.
  - *Format note:* `.claude/commands/*.md` works today and is used here for simplicity. The **current recommended form is `.claude/skills/<name>/SKILL.md`** with the same `name`/`description` frontmatter; it supports the same `/name` invocation plus autonomous use. Migrating is a one-step move (put `spec.md`'s body into `.claude/skills/spec/SKILL.md`). Use whichever; both are first-class.
- **Hooks** (`.claude/settings.json`, §8) handle automation: auto-format after edits, guardrails against dangerous shell commands, and a notification when long tasks finish. **Hooks validate at submit/commit time, never mid-edit** — blocking an edit in progress breaks the model's reasoning and produces worse code.
- **Subagents** are used for context isolation: a "research" or "doc-fetch" subagent keeps the main session's context clean by returning only its conclusion. Reach for one when a task would otherwise flood the main context.
- **Plan mode** is used for every `/plan` step — think first, write second.
- **Permissions** are pre-approved for safe, frequent operations (status, lint, test) so Claude is not interrupting for permission every few minutes, while genuinely destructive operations stay denied.
- **MCP servers** connect Claude Code to the project's surroundings: a GitHub server (manage issues/PRs/milestones from the session) and a database server for the data layer. Configured at project scope so the setup is shared and reproducible.

## 5. The command set (summary)

Full definitions live in `.claude/commands/`. In brief:

| Command | Purpose |
|---------|---------|
| `/spec` | Write a feature spec into `specs/` before any code. Kills scope creep. |
| `/plan` | Produce and review an implementation plan from a spec. No code. |
| `/verify` | Run the full gate: format, lint, types, tests, eval. Must be green. |
| `/commit` | Stage a scoped change and write a Conventional Commit. |
| `/wrap` | End-of-session: update `docs/STATUS.md` with done/next/open questions. |
| `/adr` | Record an architecture decision in `docs/adr/`. |
| `/audit` | Weekly drift check: docs vs. reality, stale specs, untested code, scope. |

## 6. Architecture decision records (ADRs)

Every decision that is expensive to reverse — a storage choice, a grounding approach, an eval definition — gets a short ADR in `docs/adr/`. ADRs are append-only and numbered; a superseded decision is marked, not deleted. This answers the question every reviewer eventually asks: *"why was it built this way?"* — and answering it well is a hallmark of senior work. Template and process in `docs/adr/README.md`.

## 7. How the project is kept from drifting

This is the explicit answer to "it's four months, how do I not lose control of it." Five mechanisms, each closing a specific failure mode:

| Failure mode | Mechanism |
|---|---|
| "I forgot where I was last session." | `docs/STATUS.md`, updated by `/wrap` every session. |
| "Scope crept and I built the wrong thing." | A `specs/` entry per unit of work, written by `/spec` *before* code. |
| "Why did I decide X three weeks ago?" | ADRs in `docs/adr/`. |
| "Am I still following the plan?" | Roadmap phases as GitHub milestones; tagged releases per phase. |
| "Did I quietly break trust or coverage?" | Eval-green invariant enforced by `/verify` and CI on every PR. |
| "The docs no longer match the code." | `/document` per change + a weekly `/audit` that flags drift. |

The throughline: **state lives in the repository, not in your head or in a chat session.** Any session — yours or Claude's — can be reconstructed from `CLAUDE.md` + `STATUS.md` + `specs/` + the ADRs.

## 8. Configuration files in this repo

| Path | Role |
|---|---|
| `CLAUDE.md` | Constitution; principles and conventions, read every session. |
| `.claude/commands/*.md` | The development-loop commands. |
| `.claude/settings.json` | Permissions and hooks (auto-format, guardrails, notifications). |
| `docs/ENGINEERING.md` | This handbook. |
| `docs/STATUS.md` | Living session journal (done / next / open questions). |
| `docs/adr/` | Architecture decision records + template. |
| `specs/` | One spec per unit of work + template. |
| `.github/workflows/` | CI: gates, eval regression, docs deploy. |
| `.pre-commit-config.yaml` | Local pre-commit gates. |

---

## 9. Definition of done

A unit of work is done when **all** of these are true:
- The spec's acceptance criteria are met.
- `/verify` is green locally and CI is green on the PR.
- The eval metrics' movement is known and acceptable (and explained if it moved).
- Docs and `CHANGELOG` reflect reality; `STATUS.md` is updated.
- A stranger could read the diff and its commit message and understand what changed and why.

A *phase* is done when every unit in its milestone is done, the demo runs end-to-end, and the release is tagged.

---

*The "what we build" lives in [`PROJECT_BRIEF.md`](PROJECT_BRIEF.md) and [`CAPABILITIES.md`](CAPABILITIES.md); the "in what order" in [`ROADMAP.md`](ROADMAP.md); the "for whom and why it matters to SAP" in [`SAP_ALIGNMENT.md`](SAP_ALIGNMENT.md). This handbook is the "how we work."*
