# Changelog

All notable changes to Tessera are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Entries are curated by hand from the project's [Conventional Commits](https://www.conventionalcommits.org/)
and rolled into a dated section at each roadmap-phase tag. Semantic version
numbers (`v0.x`) begin when the engine has its first external consumer; until
then the phase tags are the releases.

## [Unreleased]

### Added

- **The Lumière coverage gap is closed — gold coverage 1.000.** Diagnosis
  showed two deterministic causes (diacritics deleted instead of folded;
  master names carry a legal suffix the letter drops). `normalize()` now
  NFKD-folds diacritics, and document mentions tolerate a stripped legal
  suffix at reduced confidence (0.9, reason annotated). The climb
  0.929 → 0.938 → 1.000 is recorded in `eval/history.jsonl`.
- **Trust metrics tracked over time + the earned faithfulness badge.**
  `tessera-eval --record --note "why"` appends gold + synthetic numbers to the
  append-only `eval/history.jsonl` and regenerates `eval/badge.json`; the
  README now shows the faithfulness badge (deliberately withheld in Phase 0
  until the number was real and gated). Green only while the floor holds.
- **Synthetic eval battery.** Fifty-plus cases enumerated deterministically
  from the graph at eval time (no RNG, no LLM): per-entity lookups and
  aggregates, multi-step compares, per-currency superlatives, and refusal
  cases (ambiguous tokens, missing evidence, currency mixing). Expectations
  are computed from the data — never from engine output — so passing means
  something (ADR 0007). Gold and synthetic are reported separately; the
  faithfulness floor gates both.
- **Conflicting evidence is surfaced, never silently mixed.** The corpus now
  contains a deliberate conflict (an amendment moves a renewal date against
  the MSA); the engine detects disagreeing renewal dates among an entity's
  clauses and emits a conflict claim naming both values and citing both
  clauses — refusing to assert a single date. The faithfulness verifier checks
  conflict claims (quoted values must come from distinct cited clauses and
  actually disagree).
- **Multi-step reasoning.** Compare two named entities' total net order value
  (per-entity sourced step claims plus a conclusion citing both row sets) and
  currency-scoped superlative ranking — never across currencies. The
  faithfulness verifier recomputes both conclusion shapes over the graph and is
  adversarially tested to catch a wrong winner, a flipped direction, and a
  wrong entity count.
- **Question routing.** `uv run tessera` is now one routed door: the router
  classifies a question as lookup, one-entity composition, or multi-step
  reasoning — deterministically, and it prints the route and its reason above
  the answer. `--engine` forces a path; `"engine": "route"` is available to
  eval cases.

## [phase-1] — 2026-06-09

### Added

- **Evaluation harness v1 with first real trust numbers.** A deterministic
  faithfulness verifier (provably able to fail), a six-case curated gold set,
  and `uv run tessera-eval` reporting faithfulness (gated at 1.0), coverage,
  and quality. First baseline: faithfulness 1.000, coverage 0.929, quality 1.000.
- **Cross-source answer composition (`uv run tessera-compose`).** One grounded
  answer combining structured rows and document clauses for a resolved entity,
  including a fully-sourced aggregate that refuses to sum across currencies.
- **Knowledge graph with non-destructive entity resolution.** An in-process
  graph over all ingested records; deterministic name matching asserts
  reversible, confidence-carrying same-entity links; document mentions connect
  text to master data.
- **Lexical retrieval.** Deterministic BM25 over all ingested evidence (both
  modalities), refusing when nothing relevant exists; replaced the hand-authored
  question-to-claim map.
- **Universal ingestion (both modalities).** SALT-schema synthetic ERP tables
  and authored business documents enter through one ingestion door into a
  common, origin-tagged representation (modality-agnostic locators).
- **Shared quality gate.** `scripts/gate.sh` is the single source of truth run
  by both `/verify` and CI.

### Changed

- **`uv run tessera` answers from ingested data via retrieval** instead of the
  Phase 0 hardcoded knowledge.

## [phase-0] — 2026-06-05

### Added

- **Grounded hello-world (`uv run tessera`).** The smallest end-to-end path —
  question to grounded answer with claim-level provenance — answering a
  hardcoded question against in-code evidence, and declining when no evidence
  supports the question. Deterministic and model-free; it establishes the
  provenance contract the Phase 1 faithfulness metric will measure.
- **Python project (uv).** `pyproject.toml` managed by uv, with ruff
  (lint + format), mypy (strict), and pytest. Python pinned to 3.12 via
  `.python-version`, and `uv.lock` committed so the environment is reproducible
  from a clean clone.
- **Local quality gate (pre-commit).** Hooks for ruff lint/format, gitleaks
  secret scanning, and basic file hygiene, so commits are checked before they
  reach CI.
- **Continuous integration.** A GitHub Actions `gate` workflow that runs the
  same checks as the local gate — format, lint, type-check, tests, and a secret
  scan — on every pull request and push to `main`, against the locked
  environment.
- **Reproducible container.** A `Dockerfile` (pinned Python 3.12 + uv, non-root)
  and a VS Code devcontainer, so the project and its gate run identically
  anywhere with no host toolchain assumed.
- **Documentation site.** A MkDocs Material site built from `docs/` and deployed
  to GitHub Pages via GitHub Actions, with strict builds so broken links fail.
- **This changelog.**

[Unreleased]: https://github.com/robert-vetter/tessera/compare/phase-1...HEAD
[phase-1]: https://github.com/robert-vetter/tessera/compare/phase-0...phase-1
[phase-0]: https://github.com/robert-vetter/tessera/releases/tag/phase-0
