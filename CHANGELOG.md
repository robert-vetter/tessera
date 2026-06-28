# Changelog

All notable changes to Tessera are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Entries are curated by hand from the project's [Conventional Commits](https://www.conventionalcommits.org/)
and rolled into a dated section at each roadmap-phase tag. Semantic version
numbers (`v0.x`) begin when the engine has its first external consumer; until
then the phase tags are the releases.

## [Unreleased]

*(nothing yet)*

## [milestone-9] — 2026-06-28

Make entity resolution **multi-field** (name + address), closing the three
Milestone-8 residuals that name-only ER could not reach. Fully **offline and
CI-reproducible** — no embedding, no cloud (the same posture as Milestone 8).
Faithfulness gated at 1.0 throughout; the second intentional change to the ADR 0008
frozen core, kept honest by a cluster-equivalence pin, a pre-merge adversarial
review, and a measured before/after.

### Added

- **Multi-field entity resolution: the two-way address gate (ADR 0019).**
  `resolve_entities` takes an optional ordered `match_fields`; the address (already in
  the graph as `has_address` edges) is folded into the Milestone-8 stem-gate name
  decision both ways — a contradicting postal code **vetoes** an over-merge of two
  same-named firms at different locations, and an agreeing one **bridges** a
  double-typo pair the stem gate had vetoed. A hard gate, not a confidence tweak,
  because resolved entities are connected components. `resolution.compare_match_fields`
  (pure-stdlib, embedding-free) computes the agree/contradict/neutral signal by **exact
  normalized equality** (a `difflib` ratio would call `D-20095` ~ `20095` near-identical
  — caught by the adversarial review).
- **A same-name/different-address disambiguation pair** in the synthetic SALT corpus
  (two distinct "Hanseatic Trading GmbH" firms, Hamburg / Munich), appended outside the
  RNG stream so existing rows stay byte-identical. The new gold case (kind=refuse) is
  the **measured before/after**: name-only ER over-merges and wrongly answers the
  ambiguous-name question (business gold quality **0.900**); multi-field ER splits the
  firms and correctly refuses (**1.000**) — both points in `eval/history.jsonl`,
  CI-reproducible.

### Changed

- **`build_demo_graph` and `sources/salt.py` opt the business graph into multi-field
  ER** (`ADDRESS_MATCH_FIELDS = ("postal_code", "city_name")`, postal before city).
  devex / github_actions pass no `match_fields`, so their none-path is byte-identical.
  The resolved clusters are unchanged on the existing data except the one intended
  Hanseatic split (pinned, not assumed). Business gold 9 → 10, synthetic 52 → 53, every
  metric still 1.0.

### Notes

- **Second sanctioned frozen-core delta** (after Milestone 8): `graph.py` +
  `resolution.py`. A general ER capability belongs in the engine; the schema knowledge
  of which attributes are an address stays in the source (ADR 0011 pattern).
- **Measured edge kept** (the Milestone-5 discipline): two distinct firms with the same
  name *and* the same address still over-merge — only a registration/tax key separates
  them, the recorded next lever.

## [milestone-8] — 2026-06-28

Cure Milestone 7's recorded ER residual: the generic-suffix **over-merge** in the
deterministic resolution pass. Fully **offline and CI-reproducible** — no embedding,
no cloud, no online run (the inverse of Milestones 6–7). Faithfulness gated at 1.0
throughout; the first intentional change to the ADR 0008 frozen core, kept honest by
a byte-identical resolved-cluster-signature check and an adversarial review.

### Added

- **Stem-gated deterministic entity resolution (ADR 0018).** `resolve_entities`
  now confirms a `difflib` character match (≥ 0.85) only when the two names share a
  **distinctive (non-generic) signal** — a non-generic token, a near-identical
  distinctive stem, or a ≤ 2 character edit distance — so a long shared *generic*
  suffix (`… Logistik GmbH`) no longer collapses distinct firms.
  `resolution.confirm_name_match` + `resolution.corpus_generic_tokens` carry the
  gate; genericness is **corpus-derived** (a token is generic iff ≥ 3 of the names
  containing it stay dissimilar once it and the known generics are removed — iterated
  to a fixpoint so multi-token suffixes are recognised), avoiding the
  document-frequency trap that would mis-strip a token repeated across one firm's
  records (`Bayerische`).
- **Regression specimens** (`tests/test_resolution.py`, `tests/test_scale.py`):
  the over-merge cure, the multi-token-suffix cure, the short-head-typo rescue, the
  punctuated-legal-form filter, corpus-genericness permutation invariance, and the
  three recorded residuals (character-identical distinct firms, two-firm suffix
  collisions, the double-typo recall risk).

### Changed

- **`difflib` ER precision 0.50 → 1.00, labelled-set union 0.67 → 1.00**
  (`tests/test_er_metrics.py`); the `tests/test_scale.py` over-merge specimen flips
  from asserting the over-merge to asserting four distinct firms. All three eval
  batteries reproduce their Milestone-7 numbers exactly (business gold 1.0/1.0/1.0;
  devex gold 1.0/0.950/0.889; github_actions gold 1.0/0.833/0.800), and the
  business/devex resolved cluster signatures are byte-identical before and after.
- **The distinctive-stem helpers moved** from `tessera/er_semantic.py` (banned by
  the leak-guard) to the embedding-free `tessera/resolution.py`, so the engine's
  deterministic pass can share them without pulling an embedding import toward the
  faithfulness verifier (spec 0069). `er_semantic.py` re-exports them; behaviour
  byte-identical.

### Notes

- **First intentional frozen-core change** since Phase 3 (ADR 0008): `graph.py` and
  `resolution.py`. Justified — a *general* ER precision improvement belongs in the
  vertical-neutral engine, not a vertical (the opposite of ADR 0016's vertical-side
  embedding regime). Everything else in the frozen list stays empty-diff.
- **Recorded residuals → multi-field ER.** Name-only ER still cannot split two
  distinct firms with character-identical names, a two-firm suffix collision below
  the genericness floor, or a double-typo pair with no cleaner co-referent. Each is
  pinned by a test; multi-field matching (name + address + keys, ADR 0004 future
  work) is the named next lever.

## [milestone-7] — 2026-06-27

Carry the working SAP HANA embeddings **beyond retrieval** — into entity
resolution and log-chunk granularity, the two limitations Milestone 6 named.
Faithfulness gated at 1.0 throughout; embeddings stay link-only and the verifier
stays embedding-free (leak-guard extended); CI stays offline, lexical, key-free.

### Added

- **Embedding-assisted entity resolution (ADR 0016).** A second, additive
  resolution regime (`tessera/er_semantic.py`) that proposes same-entity
  `Resolution`s from the cosine of two names' **distinctive stems** (the name
  minus its generic tokens). One stem-gated rule resolves the opposite-direction
  ER tension: it bridges the undeclared `checkout-svc` abbreviation (recall) while
  distinct generic-suffix firms reduce to distinct stems (precision). Additive and
  reversible; applied vertical-side; the engine `resolve_entities` stays
  embedding-free.
- **A HANA-native ER path.** `propose_semantic_resolutions_via_index` embeds the
  stems in-database (vectors never enter Python), sharing the stem-gating core
  with the provider path.
- **ER precision/recall, measured (`tests/test_er_metrics.py`).** A labeled
  pair-set scores `difflib` (0.50 / 0.50) vs the stem-embedding regime
  (1.00 / 1.00) — a reported measurement, not a new gated floor.
- **Finer log chunking with stable chunk ids (ADR 0017).** `parse_log_chunks`
  isolates a runner log's `##[error]` cluster into its own short chunk, so the
  Pages-deploy 404 surfaces instead of diluting under ~49 lines of provisioning.
  Chunk ids became role-tagged (`chunk{n}`/`error{n}`), stable across re-chunking.
- **Two recorded eval cases + their online closes.** A devex on-call lookup
  (offline gold coverage 0.950 — `checkout-svc` unresolved) and the de-diluted
  synonymy case (offline 0.833); one SAP HANA one-shot closed **both** to
  1.000 / 1.000, faithfulness 1.0, recorded in `eval/history.jsonl`. Earned, not a
  re-saturation: distinct services did not over-merge online.
- **`tessera-eval --recorded YYYY-MM-DD`** to stamp a one-shot online point; the
  DEPLOYMENT runbook gained the Milestone-7 one-shot.

### Notes

- The embedding regime is *additive*, so it cannot remove `difflib`'s existing
  generic-suffix over-merge; stem-gating the `difflib` pass or multi-field ER is
  the recorded next lever (WRITEUP limitations).
- A real-model finding: HANA embeddings are asymmetric (`QUERY`/`DOCUMENT`), so
  identical text scores ~0.889 — above threshold, the close holds with margin.
- Engine core unchanged: `git diff milestone-6..milestone-7` over the ADR 0008
  frozen list is empty.

## [milestone-6] — 2026-06-27

Act on ADR 0010: real semantic embeddings, **run on SAP HANA Cloud**, to close
the error-class-synonymy miss Milestone 5 deliberately kept. Faithfulness gated
at 1.0 throughout; CI stays offline, lexical, and key-free.

### Added

- **Embedding + vector seams (ADR 0015).** An `EmbeddingProvider` protocol + a
  GenAI Hub adapter (stdlib HTTPS, contract-tested); a `VectorStore` protocol
  with an in-memory backend and a HANA Cloud backend (`REAL_VECTOR` +
  `COSINE_SIMILARITY`). `hdbcli` is an opt-in `cloud` extra, imported lazily — the
  default clone-and-run stays pure-stdlib (guarded by a test).
- **HANA-native embeddings.** `HanaSemanticIndex` embeds in-SQL via
  `VECTOR_EMBEDDING` (vectors never enter Python); the GenAI Hub → HANA pivot is
  recorded as an ADR 0015 addendum.
- **Semantic retrieval with lexical fallback.** A `SemanticRetriever` protocol;
  retrieval is semantic when configured, else exactly ADR 0003 lexical. A
  subprocess **leak-guard** pins that the faithfulness verifier imports no
  embedding module — a 1.0 stays earned by structure, not a model.
- **The synonymy gold case + the recorded close.** A `github_actions` gold case
  lexical cannot bridge (offline gold coverage 0.833) that HANA embeddings close
  online (coverage/quality 1.000) — both points in `eval/history.jsonl`. The
  first named miss closed by a method upgrade, measured on cloud infrastructure.
- **Deployment runbook + `.env.example`** for the HANA-native path (the NLP
  feature, a least-privilege app user, a smoke test, the one-shot record).

### Fixed

- HANA existence-check casing (HANA upper-cases unquoted identifiers) so the
  vector table is not re-`CREATE`d on every run.

### Notes

- The online embedding number is a **timestamped measurement, not
  CI-reproducible** — CI stays on the lexical path. SAP's embedding shows
  long-document dilution (the answer surfaces the failed run, not the diluted 404
  log line) — recorded as a named limitation.

## [milestone-5] — 2026-06-16

Post-roadmap hardening: make the eval able to fail again. Every roadmap number
had reached 1.000 and both synthetic batteries had saturated (ADR 0007 trigger
2); a floor that cannot fail is decorative. This milestone reintroduces failure
with **un-planted** difficulty, holding faithfulness gated at 1.0 throughout.

### Added

- **The first real connector — GitHub Actions (ADR 0014).** The repo's own CI
  history is ingested through the same door, reusing the table-row and log-span
  locator kinds with zero engine change. The live fetch is a run-once script
  (the only network touchpoint); the snapshot is committed, scrubbed, and
  byte-reproducible. A new `github_actions` eval battery measures it.
- **A measured, un-planted miss — and its deterministic close.** Real CI logs
  mark failures `##[error]` (not the synthetic `ERROR <svc>:`), so the saturated
  eval finally measured a miss no one authored: github_actions gold coverage
  **0.000**, quality 0.500. An additive close (real run-id grammar, `##[error]`
  recognition, first-`##[error]`-line signature) recovered it to **1.000**,
  including a genuine cross-run recurrence over two real Pages-deploy failures.
  The drop and recovery are both recorded in `eval/history.jsonl`.
- **Mixed-modality multi-hop in one turn.** RCA walks the incident ticket to the
  PR that resolved it and the diff that did it (`run → log → log → ticket → PR →
  diff`, each hop cited), closing the gap Phase 2 named; the mis-pivot trap is
  avoided structurally.
- **Free-form phrasing variety.** The router gained superlative synonyms,
  word-boundary matching, and currency-set validation; the batteries now sample
  phrasing. Two latent router bugs (`most`⊂`almost`; any-uppercase-triple as a
  currency) fixed.
- **A scale stress harness.** The engine is faithful and ER-precise over 180
  entities; the transitive over-merge risk is measured at volume.
- **Three standing-trigger specimens.** ADR 0005 (a verbatim-but-misleading
  claim passes the structural check), ADR 0010 (error-class synonymy no declared
  alias could bridge), ADR 0006 (the intent-verb router ceiling) — each a
  committed test; none acted on (the determinism line held).

### Changed

- **The faithfulness floor now gates the build.** `tessera-eval` runs inside the
  shared `scripts/gate.sh`, so a floor breach fails CI, not only the local
  `/verify` step (it previously ran in no automated gate).
- WRITEUP gains a post-roadmap hardening section and updated, more honest
  limitations (scale now partly tested; the real connector now exists).

## [phase-4] — 2026-06-10

### Added

- **The first full trust loop closed on a public number (ADR 0010).** The
  measured devex coverage gap (0.917 — the named `notif-svc` miss, similarity
  0.429) is fixed the way a real organization would: the service catalog
  **declares the alias**, the vertical asserts it as an ordinary reversible
  `Resolution` (confidence 1.0, reason naming the declaration), and a new
  graph-aware **service route** answers on-call/ownership questions from the
  resolved entity. Devex gold coverage **0.917 → 1.000**, recorded.
  Embeddings were reassessed and deferred again with a refreshed trigger (a
  measured miss no declarable data could fix); `checkout-svc` (0.846) stays
  deliberately undeclared as the mechanism's visible boundary.
- **The Joule-style session — `uv run tessera-chat` (ADR 0013).** One
  conversational door over both verticals: explainable routing, numbered
  claims, `:show N` walks a claim to its records, locators, snapshot date,
  and resolution/mention assertions; `:trust` shows the recorded battery
  numbers; every answer is re-verified live by the same verifier the eval
  uses. Optional LLM narration renders below the canonical claims under a
  visible label, behind a deterministic novelty guard (fabricated numbers/ids
  are discarded with a notice); refusals are never narrated; no key — no
  narration, and nothing changes.
- **The SAP deployment path (ADR 0012).** `docs/DEPLOYMENT.md` maps each
  component to its SAP service (GenAI Hub on AI Core for models; HANA Cloud
  as the documented graph/vector target; BTP runbook) and separates what CI
  verifies from what needs credentials. `tessera/platform/` is the only
  cloud-aware code: env-derived config defaulting to local mode and two
  stdlib-HTTP `ModelProvider` adapters (SAP GenAI Hub; Anthropic as the
  locally demoable fallback), contract-tested against fakes. No provisioning
  (asked and declined); CI stays key-free; zero new dependencies.
- **The technical write-up** (`docs/WRITEUP.md`): problem, architecture, how
  the metrics are earned, the recorded coverage trail (business
  0.929 → 0.938 → 1.000; devex 0.917 → 1.000), the generality proof,
  limitations at full prominence, deferred future work, and the
  reproduce-everything commands.

### Changed

- **The namespace asymmetry ADR 0008 recorded is repaired.** The business
  answer layer moved to `tessera/business/` beside `tessera/devex/` (the
  business synthetic generator left its misleading `eval/synthetic.py` home);
  core `tessera/routing.py` keeps only the shared `Route` contract. Both
  batteries' numbers reproduced exactly.
- **Verticals own their claim grammars (ADR 0011).** The six business
  verifier shapes moved from `eval/metrics.py` to `tessera/business/claims.py`
  and reach the verifier via `Battery.claim_shapes`; the metric core keeps
  only the generic grammars (verbatim containment, shared fragment) and a
  leak-guard test pins it vertical-free. The devex battery declares no
  grammars — its claims need only the generic ones.

### Fixed

- README front-door drift: stale pre-fix eval output, a missing
  `tessera-chat`, and one **overclaim** (agentic workflows / MCP support
  asserted as present) corrected to the truthful future-work framing.
- Changelog footer compare-links: `phase-2`/`phase-3` were missing and
  `Unreleased` still compared against `phase-1`.

## [phase-3] — 2026-06-10

### Added

- **The DevEx Copilot — a second vertical on a provably unchanged core.**
  CI/CD runs with full logs, PR diffs, ticket history, a service catalog,
  and an on-call export (deterministic synthetic corpus,
  `data/devex_synthetic/`, generated with **no RNG** — every record a
  reviewable literal) arrive through the *same* `Ingester` door, with two
  new locator kinds (`log-span`, `diff-hunk`) riding the unchanged
  kind-tagged `Locator`. The phase-close audit shows every frozen core file
  **byte-identical to `phase-2`** (ADR 0008) — the milestone "two genuinely
  different verticals run on one unchanged core" as an empty diff, not an
  assertion.
- **Root-cause analysis grounded in log lines** (`uv run tessera-devex`):
  the failing run's outcome row and error log sections verbatim, a
  *recurrence* claim when the same error signature appears in an earlier
  run's log, and a *documented incident* claim when a ticket quotes it.
  First occurrences get no recurrence claim; passed runs are refused
  premises; unknown runs are refused by name.
- **PR change-summaries tied to motivating tickets**: the diff itself,
  hunk by hunk, plus a verifiable link claim (the ticket id appears in both
  the PR row and the ticket row). A PR that names no ticket gets a summary
  without one — honest omission.
- **One vertical-neutral verifier shape** (the only verifier change, ADR
  0008): a shared-fragment claim — `"FRAGMENT" appears in 'A' and 'B'` —
  verified by recomputation (≥2 citations, named sources == cited origins
  exactly, fragment present in every cited record), adversarially tested
  with vertical-free fixtures.
- **Eval batteries (ADR 0009).** The harness scores any number of verticals
  with one shared, unchanged scoring function; verticals are bound in one
  registry line. History gains append-only v2 lines; the badge becomes the
  *minimum* gold faithfulness across batteries. The refactor reproduced the
  business numbers exactly (gold 7 / synthetic 52, all 1.000).
- **First two-vertical numbers** (recorded in `eval/history.jsonl`):
  business gold/synthetic and devex synthetic all **1.000**; devex gold
  **faithfulness 1.000, coverage 0.917, quality 1.000** — the coverage gap
  is the *named* `notif-svc` on-call miss (similarity 0.429; no shared
  retrieval token), planted in the corpus, predicted in spec 0033 before
  the battery ran, and kept as the measured trigger for the next trust
  loop (ADRs 0003/0004).

### Fixed

- Doc drift: the ADR index (`docs/adr/README.md`) and the mkdocs nav now
  list every ADR; the Phase 2 changelog entries below are rolled into their
  phase section (they had lingered under "Unreleased" past the tag).

## [phase-2] — 2026-06-10

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

[Unreleased]: https://github.com/robert-vetter/tessera/compare/phase-4...HEAD
[phase-4]: https://github.com/robert-vetter/tessera/compare/phase-3...phase-4
[phase-3]: https://github.com/robert-vetter/tessera/compare/phase-2...phase-3
[phase-2]: https://github.com/robert-vetter/tessera/compare/phase-1...phase-2
[phase-1]: https://github.com/robert-vetter/tessera/compare/phase-0...phase-1
[phase-0]: https://github.com/robert-vetter/tessera/releases/tag/phase-0
