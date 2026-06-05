# 0006. CHANGELOG

- **Phase / milestone:** Phase 0 — Foundation and frame (housekeeping)
- **Issue:** (none yet)
- **Status:** implemented

## Problem

`docs/ENGINEERING.md` §3 calls for a `CHANGELOG` driven by the project's
Conventional Commits, plus semantic-version tags per roadmap phase. A changelog
is the human-readable counterpart to the commit history: it tells a reader
*what changed for them* between versions, without spelunking git. The project
already commits conventionally and will tag `v0.1.0` after Phase 1, so the
changelog should exist now (seeded with an `Unreleased` section) and be ready to
cut its first release at the Phase 1 tag.

## Acceptance criteria

- [ ] `CHANGELOG.md` at the repo root in **Keep a Changelog** format, noting it
      adheres to **Semantic Versioning** and that entries derive from
      Conventional Commits.
- [ ] An **`[Unreleased]`** section summarizing the Phase 0 scaffolding landed so
      far (project config, pre-commit, CI, devcontainer, docs site), grouped by
      Keep-a-Changelog category (Added / Changed / …).
- [ ] The file passes the repo's existing gates (pre-commit hygiene hooks;
      markdown is well-formed).
- [ ] A short note documents how the changelog is maintained going forward
      (hand-curated under `[Unreleased]`, rolled into a version section at each
      phase tag) — and, if automation is chosen, how to regenerate it.
- [ ] No fabricated history: entries reflect commits that actually landed.

## Scope

**In:** `CHANGELOG.md` seeded with the real Phase 0 work and an `[Unreleased]`
section; a brief "how this is maintained" note (in the file and/or a line in the
README/SETUP); optionally a changelog-automation config if that path is chosen
(see open question).

**Out:** cutting an actual versioned release or git tag (that happens at the end
of a roadmap phase, not here); release-notes publishing to GitHub Releases;
restructuring commit conventions; and the README **badges** (unit 8).

## Eval impact

None. Housekeeping/documentation; it touches no faithfulness/coverage/quality
metric (the eval harness arrives in Phase 1).

## Risks / open questions

- **Hand-maintained vs automated** — **confirmed hand-curated** Keep-a-Changelog
  (full editorial control, no new tooling; kept current via `/document` in the
  loop). git-cliff automation remains an easy later swap if manual upkeep
  becomes a burden. Cheap to reverse — **no ADR**.
- **Keeping it honest.** Whatever the mechanism, entries must match reality;
  `/document` in the loop keeps it current per change.
