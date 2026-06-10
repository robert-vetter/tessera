# CLAUDE.md

Working instructions for building **Tessera** with Claude Code. Read this before doing anything. The "what" and "why" live in [`README.md`](README.md) and [`docs/`](docs/); this file is about *how we work* on it.

---

## What this project is (one paragraph)

Tessera is a trust layer for enterprise AI agents. It ingests heterogeneous data (structured + unstructured), resolves entities across sources into one knowledge graph, answers questions conversationally with **claim-level provenance**, and **measures its own faithfulness** with a benchmark harness. Two reference verticals (Business Data Copilot, DevEx Copilot) run on one shared engine. It is being built deliberately over several months. Full context: [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md).

## Non-negotiable principles (apply to every change)

1. **Groundedness over fluency.** Never produce an answer path that can't trace to evidence. A correct refusal beats a confident guess.
2. **Provenance is mandatory.** Every claim carries a path back to its source records. If a feature would break that, it doesn't ship.
3. **Trust is measured.** No capability is "done" until its effect on the faithfulness/coverage/quality metrics is known. Keep the eval runnable at all times.
4. **Structured and unstructured are equal.** Don't bolt one onto the other.
5. **Engine stays general.** Vertical-specific logic (business vs. DevEx) never leaks into the core.
6. **Vertical slice first.** Always prefer a thin end-to-end path over a broad half-built layer.
7. **Honest scope.** No vaporware. If something is deferred, say so in the write-up's "future work."

## How to work in this repo

- **Follow the roadmap phases** in [`docs/ROADMAP.md`](docs/ROADMAP.md). Don't jump ahead to breadth before the current phase's vertical slice works.
- **Small, frequent, honest commits** with clear messages that reflect real progress. The commit history is part of the deliverable.
- **Keep the demo working.** At the end of any work session there should be something runnable.
- **Keep the eval green and meaningful.** If a change moves the metric, note why. Never silently disable a check to make numbers look good.
- **Document as you go.** When you finish a unit of work, update the relevant doc and jot what works / what doesn't / what was learned. This material feeds the final write-up.
- **Prefer SAP-native primitives** where they fit (model orchestration, graph/vector storage) per [`docs/SAP_ALIGNMENT.md`](docs/SAP_ALIGNMENT.md), but keep a portable local mode so development doesn't depend on cloud access.

## Conventions

- **Language:** all code, comments, docs, commit messages, and the write-up in **English**.
- **Clarity over cleverness.** This codebase exists partly to be *read* by a reviewer. Favor obvious, well-named, well-documented code.
- **Reproducibility.** Anyone should be able to clone and run the current state from the README. Keep setup honest and current.
- **Tests track trust.** The evaluation harness is not an afterthought; treat its health like the build's health.

## Guardrails — things NOT to do

- Do not add a claim to an answer without provenance, even temporarily.
- Do not let the faithfulness metric become decorative — keep its definition transparent and its inputs auditable.
- Do not expand the connector list or add sources for their own sake before the core generalizes across the first two.
- Do not overclaim in docs or write-up. "Integrated and measured hard, separate pieces" is the true and stronger story; "invented something that doesn't exist" is neither.
- Do not start foundation-model training from scratch. A focused, well-explained adaptation of the matching/embedding component is the ceiling here.

## When unsure

Re-read the relevant doc in `docs/` and the principles above. If a decision trades off against a principle, the principle wins. If genuinely ambiguous, leave a clearly marked note and a question in the code or commit rather than guessing silently.

## Definition of done (per phase)

A phase is done when: its milestone in the roadmap is true, the demo runs, the eval runs and its numbers are known, the docs reflect reality, and a stranger could follow what changed and why.

## Workflow, tooling, and anti-drift

The full operating manual is [`docs/ENGINEERING.md`](docs/ENGINEERING.md). The essentials, which apply every session:

- **Follow the development loop:** `/spec` → `/plan` → implement → `/verify` → `/document` → `/commit` → `/wrap`. The commands live in `.claude/commands/`. Don't skip `/spec` (it stops scope creep) or `/wrap` (it stops session drift).
- **State lives in the repo, not in memory.** At the start of a session, read `docs/STATUS.md` and the relevant `specs/`. At the end, run `/wrap` to update `STATUS.md`. Any session must be resumable from written state.
- **`/verify` is the gate before every commit:** format, lint, types, tests, eval. Never commit on red; never weaken a check or the eval to pass.
- **Record hard-to-reverse decisions** with `/adr` into `docs/adr/`.
- **Run `/audit` weekly** to catch docs-vs-reality drift, untested code, and scope creep.
- **Conventional Commits, small and frequent.** Tag a release at the end of each roadmap phase.
- Hooks auto-format after edits and guard against destructive shell commands; they never block mid-edit. Don't move logic that belongs here into hooks.

When a session starts cold, the reading order is: this file → `docs/STATUS.md` → the relevant `specs/` entry → the relevant `docs/`.

### Autonomous phase execution

From Phase 2 onward, a whole roadmap phase may run **autonomously** from a single
kickoff prompt. The discipline does not change — only the interactive stops do:

- **Same artifacts, no approval pauses.** Every unit still gets its `specs/`
  entry before code, an ADR when a choice is hard to reverse, a green gate
  (`scripts/gate.sh` + eval), and a branch → PR → CI-green → merge. The agent
  approves its own spec/plan and **records the decision and its rationale in the
  spec/ADR** instead of asking.
- **Branch first, always.** Create the unit's feature branch before any commit
  (branch protection enforces this; it has caught violations before).
- **Decide upfront, then execute.** At phase start, read `docs/STATUS.md`, the
  roadmap phase, and the ADR revisit-triggers; fix the phase's unit breakdown and
  key decisions; record them as the phase proceeds.
- **Ask only project-shaping questions.** Interrupt the maintainer only for
  decisions that change what the project *is* (scope, licensing, external
  services/spend, anything irreversible at project level). Everything else:
  decide, record, proceed.
- **Honesty rules still bind.** Never weaken the gate or the eval to keep the
  phase moving; a unit that cannot be finished honestly is reported, not faked.
- **Close the phase.** `/wrap` STATUS, update the CHANGELOG, tag `phase-N`, and
  hand back a summary plus a paste-ready kickoff prompt for the next phase.
