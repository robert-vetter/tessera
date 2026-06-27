# 0051. Milestone 6 plan: embeddings on SAP — close the undeclarable miss (designed-for → ran-on)

- **Phase / milestone:** Milestone 6 — Embeddings on SAP (post-roadmap; ROADMAP
  phases complete and tagged `phase-0`…`phase-4`; hardening tagged `milestone-5`)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018: decisions recorded here
  instead of asked — except the two project-shaping questions below, which were
  asked)

## Problem

Milestone 5 made the eval able to fail again and then, deliberately, **left a
miss un-closed**: the three live revisit triggers each got a concrete committed
specimen (`tests/test_trigger_specimens.py`), none acted on, because the
maintainer chose to hold the determinism line. The sharpest of the three is
ADR 0010's refreshed embeddings trigger, and it is the only one backed by a
*measured, undeclarable* miss:

In the repo's own real GitHub Actions Pages-deploy failure, **one** root cause
surfaces as three mutually un-bridgeable strings —

- `HttpError: Not Found`
- `status: 404`
- `Ensure GitHub Pages has been enabled`

— pairwise string-similarity `< 0.35`, all three verified present in the
committed real log (`test_adr0010_error_class_synonymy_is_undeclarable`). A
declared catalog alias closed the *declarable* `notif-svc` name variance in
Phase 4 (ADR 0010); **no catalog field can declare "404 means
Pages-not-enabled."** Only semantics can link them. That is the exact firing
condition the refreshed trigger was written to watch for: *a measured coverage
miss caused by vocabulary variance that no one can fix by declaring data.*

The maintainer has now authorized crossing the determinism line for this one,
earned case — and doing it the way ADR 0010 / ADR 0003 always specified:
**SAP Generative AI Hub embeddings + HANA Cloud vector store, with the lexical
BM25 path as the portable offline fallback.** The deliverable that makes this
real (not "designed for") is a **recorded online measurement**: the
error-class-synonymy case scored as a miss by the offline lexical path and as a
close by the online embedding path, both committed to `eval/history.jsonl`.

**Maintainer decisions (asked 2026-06-27, because they are project-shaping):**

1. **Next milestone = act on ADR 0010 (embeddings), the cloud "ran on SAP"
   variant** — chosen over the no-spend local-pretrained-embedding variant, a
   second real connector, agentic/MCP mode, and BTP-provisioning-only. This is
   the one move the project's own thesis selects: the metric has shown the
   deterministic layer missing on data no declarable field can fix, which is the
   precise, pre-committed condition for upgrading the method. **Authorizes
   provisioning spend** (confirmed again at the Unit 7 measurement).
2. **Access path = keys available now.** The maintainer provisions SAP AI Core +
   HANA Cloud and supplies credentials into a gitignored local `.env` (never
   committed; CI stays key-free). The one-time online measurement therefore runs
   **this** milestone and the real number is recorded — true "ran on SAP," not a
   deferred runbook. HANA Cloud is provisioned (instance reachable on `:443`;
   `DBADMIN` creds captured); the GenAI Hub **embedding deployment** is the one
   remaining provisioning piece, buildable around (Units 1–6 are offline).

**HANA instance shape (recorded, decided during provisioning):** vector engine
only — **no** NLP feature (in-database `VECTOR_EMBEDDING` is not used; embeddings
are generated at GenAI Hub), **no** PAL, **no** data lake. The `REAL_VECTOR`
type + `COSINE_SIMILARITY` KNN are HANA Cloud core and need no feature toggle.
Rationale and the in-DB-embeddings alternative are noted in ADR 0015.

## The re-inverted success criterion

Milestone 5 succeeded by the *inverted* shape — surfacing a miss and **keeping**
a recorded sub-1.0 specimen (the anti-saturation end state). Milestone 6
succeeds by the **mirror** shape, and the distinction is the point:

- **The kept specimen is closed — with semantics, and the close is recorded
  online.** The error-class-synonymy case (un-bridgeable by lexical) is added to
  the `github_actions` battery; the **offline lexical path scores it a miss**
  (recorded), the **online embedding path closes it** (recorded). Faithfulness
  1.0 at both points.
- **The close is earned, not a re-saturation.** A semantic linker that bridges
  `404 ≈ Not Found ≈ Pages-not-enabled` could *also* wrongly merge distinct
  services. So the milestone measures **precision as well as recall** and reports
  both: the deliberately-retained `checkout-svc` 0.846 near-miss and the distinct
  on-call/catalog services must **not** be falsely linked by embeddings. A method
  that fixes one miss by creating a worse one is a **recorded finding**, not a
  hidden trade — and would itself fire a fresh trigger.
- **Faithfulness stays gated at 1.0 throughout, never weakened or re-defined.**
  Embeddings change *what is retrieved/linked*, never *what is claimed*:
  `eval/metrics.py` (`is_supported`) stays deterministic, structural, and
  **embedding-free** (leak-guarded by a test). The claim path is frozen.
- **CI stays key-free and offline on the lexical fallback.** The embedding win is
  a **timestamped one-time online measurement** (the Milestone-5 live-fetch
  precedent), not a CI-reproducible number — because the embedding model lives in
  the cloud and may change. This asymmetry is stated honestly, not hidden.
- **The default clone-and-run stays pure-stdlib.** `hdbcli` (SAP's HANA driver,
  a binary wheel) is an **opt-in extra**, lazily imported, never in the default
  `uv sync` or CI import graph (guarded by a test).
- If the online run cannot be made to honestly move the number, that is
  **reported plainly**, and the milestone ends with the seam built + a pending
  measurement rather than a fabricated 1.000.

## Acceptance criteria

- [ ] **Embedding-provider seam.** An `EmbeddingProvider` protocol alongside the
      existing `ModelProvider`; a `GenAIHubEmbeddingProvider` (stdlib HTTPS,
      OAuth2 client-credentials, contract-tested against a **fake transport**);
      config additions (`AICORE_*` embedding deployment id + `HANA_*`);
      `embedding_provider_from_env` returns `None` in the default local mode. No
      cloud is touched in tests. **ADR 0015** records the architecture.
- [ ] **Vector-store seam + HANA backend.** A `VectorStore` interface; a HANA
      Cloud backend (`REAL_VECTOR` column, upsert, KNN via `COSINE_SIMILARITY`)
      using `hdbcli` as a **cloud-only optional dependency**, imported lazily;
      contract-tested against a fake. A test/check proves the default import
      graph carries **no** `hdbcli`/cloud import (pure-stdlib clone-and-run
      preserved).
- [ ] **Semantic retrieval/linking behind the seam, lexical fallback.** The
      semantic strategy is active only when both an embedding provider and a
      vector store are configured; otherwise the engine falls back to **lexical
      BM25** (ADR 0003/0010 stated end state). Built to bridge the
      error-class-synonymy specimen. The engine claim path is unchanged.
- [ ] **The synonymy gold case + the precision guard.** The `github_actions`
      battery gains the error-class-synonymy gold case: **lexical = recorded
      miss; semantic (online) = recorded close**, faithfulness 1.0 at both. A
      **precision check** proves embeddings do **not** over-link the
      `checkout-svc` near-miss or distinct services; recall and precision are
      both reported.
- [ ] **Deployment + least-privilege user.** `docs/DEPLOYMENT.md` gains the
      GenAI Hub embedding-deployment + HANA vector provisioning runbook;
      `.env.example` is committed; the app connects as a **dedicated
      least-privilege HANA user** (its own schema), not `DBADMIN`; the
      verified-vs-not split is updated to mark the embedding/HANA path
      **verified (ran on)** once the Unit 7 number lands.
- [ ] **The online measurement (spend, maintainer-confirmed).** With the GenAI
      Hub embedding deployment provisioned and per-run cost confirmed, run
      `tessera-eval --record` **online once** against GenAI Hub + HANA; commit
      the real number(s) to `eval/history.jsonl` with a note. Faithfulness 1.0.
- [ ] **Close.** Gate green under multiple `PYTHONHASHSEED` values (offline
      lexical path); WRITEUP "ran on SAP" + embeddings section citing the
      recorded number; README numbers; CHANGELOG `[milestone-6]`; STATUS; tag
      `milestone-6`; memory; next-milestone kickoff handed back.

## Scope

**In — the unit breakdown (one PR each, spec each):**

| Unit | Spec | Content |
|---|---|---|
| 1 | 0051 | this plan |
| 2 | 0052 | embedding-provider seam: `EmbeddingProvider` protocol + `GenAIHubEmbeddingProvider` (stdlib HTTPS, fake-transport contract tests); config (`AICORE_*` embedding deployment, `HANA_*`); **ADR 0015** (embeddings architecture: GenAI Hub generation + HANA vector store + lexical offline fallback + online-measured number + `hdbcli` opt-in extra) |
| 3 | 0053 | vector-store seam + HANA backend (`REAL_VECTOR` schema, upsert, KNN via `COSINE_SIMILARITY`); `hdbcli` opt-in extra, lazy import; default-import-graph purity test; fake-backed contract tests |
| 4 | 0054 | semantic retrieval/linking strategy behind the seam; lexical BM25 offline fallback; built to bridge the synonymy specimen; engine claim path frozen; verifier embedding-free leak-guard |
| 5 | 0055 | eval cloud-mode: the error-class-synonymy gold case (lexical miss / semantic close) + the precision guard (no over-merge); harness semantic mode; offline default unchanged and CI-stable |
| 6 | 0056 | `docs/DEPLOYMENT.md` runbook (GenAI Hub embedding deployment + HANA vector) + `.env.example` + dedicated least-privilege HANA user; verified-vs-not split |
| 7 | 0057 | **the online measurement** — provision/confirm, run online once, record the real number(s) in `eval/history.jsonl` (maintainer-confirmed spend) |
| 8 | 0058 | close: WRITEUP/README/CHANGELOG/STATUS, tag `milestone-6`, memory, kickoff |

**Out (explicitly):**

- **The no-spend local-embedding variant.** Embeddings are generated at GenAI
  Hub, not by a bundled local model; the offline fallback is the **lexical** path
  (which honestly cannot bridge the synonymy — that is why CI coverage may read
  `< 1.0` offline while the online number reads the close).
- **Embeddings on the claim / faithfulness path.** `is_supported` stays
  deterministic and structural; ADR 0005's LLM-judge stays deferred. Embeddings
  serve retrieval/linking only.
- **HANA as general graph persistence.** Only the vector store lands; the graph
  stays the embedded in-process `KnowledgeGraph` (ADR 0004). Full HANA
  persistence remains future work.
- A **second real connector**; **agentic/MCP** mode; **multi-field ER** beyond
  what embeddings provide; persistence/multi-tenancy/security hardening. These
  remain the WRITEUP's named future work.

## Eval impact

The first milestone whose intended impact is to **close a previously-recorded,
named sub-1.0 specimen with a method upgrade**, and to prove the upgrade earns it
without re-saturating:

- **Recall up:** the error-class-synonymy case moves from miss → close via
  semantic linking, recorded **online** in `eval/history.jsonl` (offline lexical
  still records it as a miss — both points kept, the trust-loop pair).
- **Precision measured:** the retained `checkout-svc` near-miss and distinct
  services are checked to remain **unlinked** under embeddings; reported
  alongside recall. An over-merge is a recorded finding, not hidden.
- **Faithfulness pinned at 1.0** at every recorded point. Any drop is a real bug
  (embeddings must not leak into claims), never a new normal.
- **Offline numbers unchanged.** The lexical path that CI runs is untouched; the
  default batteries read exactly as Milestone 5 left them.

## Risks / open questions

- **Non-determinism of the cloud model.** Embeddings are deterministic given a
  fixed model+input, but the GenAI Hub model can change under us. The embedding
  number is therefore a **timestamped online measurement** (like M5's live
  fetch), not CI-reproducible; CI stays on lexical. Stated honestly in U5/U7 and
  STATUS, so a reviewer cloning at HEAD understands which number is reproducible
  and which is a recorded online fact.
- **Over-merge (the central technical risk).** A semantic linker strong enough to
  bridge `404 ≈ Not Found` may wrongly bridge distinct services. The precision
  guard (U5) is non-negotiable: measure both recall and precision; pick the
  similarity threshold against *both* the synonymy close and the no-false-merge
  constraint; if no threshold satisfies both, that is the recorded finding and
  the honest answer (semantics helped recall but cost precision — a fresh,
  named trade), not a silently-tuned number.
- **Faithfulness-leak risk.** Embeddings must touch retrieval/linking only. The
  leak-guard: a test asserts `eval/metrics.py` imports nothing from the
  embedding/vector modules, so a 1.0 stays earned by structure, not by a model.
- **Dependency creep.** `hdbcli` is a binary wheel; keep it an opt-in extra
  (`uv sync --extra cloud`), lazily imported; a test pins that the default
  import graph has no cloud import, preserving clone-and-run. The HANA backend
  module must import `hdbcli` inside functions, never at module top level.
- **Cost.** Each online eval run embeds a few hundred short texts once + a
  handful of KNN queries — small. Pin record counts; confirm per-run cost with
  the maintainer **before** the U7 run; do not loop the online eval.
- **Security.** Connect as a dedicated least-privilege HANA user (own schema),
  not `DBADMIN`; the `DBADMIN` password reached the chat transcript, so recommend
  rotating it after the milestone (noted in U6). `.env` is gitignored; gitleaks
  guards commits.
- **ADR 0010 is now *acted on*.** ADR 0015 records the crossing and the evidence
  that justified it (the committed undeclarable specimen + the maintainer's
  explicit go-ahead + spend authorization); ADR 0010 gets an addendum pointing to
  it. This is the first time the project takes on a model/cloud runtime
  dependency — the boundary (cloud-only, opt-in, retrieval-only, faithfulness
  untouched) is the thing ADR 0015 must make crisp.
- **Engine-leak risk.** The seam lives in `tessera/platform/` + a thin
  retrieval-strategy switch; vertical-neutral. The semantic-linking *application*
  (which records embed, which battery uses it) stays vertical-side. Guarded by
  the empty-diff core check at close (ADR 0008).
