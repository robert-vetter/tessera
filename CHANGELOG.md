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

## [milestone-17] — 2026-07-03

Demoable to humans: the presentation layer as a strict consumer of the existing
trust objects — no engine, verifier, or boundary change; every battery number
byte-identical throughout. Closes with the hosted demo **live** at
<https://robert-vetter-tessera.hf.space>.

### Added

- **The web surface** (`uv run tessera-ui`; spec 0114, ADR 0027, #128): one
  page, pure stdlib, zero JavaScript, strict CSP, escape-everything — ask →
  routed answer with per-claim verifier chips → provenance drill-down (records,
  locators, ER trail) → refusal cards → action draft → dry-run payload →
  explicit approve → **simulated** receipt. Holds no credential; no code path
  to the real actuator. Three focused adversarial reviews (security ×2,
  trust-honesty): **0 majors**; all confirmed minors fixed and pinned.
- **A real Claude agent grounded only through the MCP tools** (spec 0115,
  #129): `scripts/record_agent_session.py` + the committed
  `data/agent_session/` transcript — grounded RCA with cited evidence, a
  refusal carried honestly (run R-1041 passed), and an action ending at a
  simulated receipt.
- **Hosting + assets** (spec 0116, #130/#131/#134/#135): `docs/DEMO.md`
  (key-free hosting runbook, the 3-minute demo script, the EN+DE one-pager)
  and the two-file Hugging Face Space under `deploy/hf-space/`.

### Changed

- **Narration exercised live for the first time** (spec 0113, #127; ADR 0013
  boundary held: labelled, below the canonical claims, refusals un-narrated);
  `narrate_texts` extracted so chat and UI share one guard. `:trust` renders
  three-decimal metrics; MCP `serverInfo.version` reports the project version.

## [milestone-16] — 2026-07-03

Close & clean — the Act 2 opener: a full self-audit acted on **before** the first real
side effect. Drift repaired, the side-effect-capable surface hardened (with a 5-lens
adversarial review that found and fixed three majors in the fixes themselves), the
verifier's blind spots named and its accounting widened, and the Milestone-15 one-shot
prepared down to two maintainer commands.

### Added

- **Act 2 planning corpus** (#118, #119): the 2026-07-02 repository audit
  (`docs/AUDIT_2026-07-02.md`), the sourced market snapshot (`docs/MARKET.md`),
  the Act 2 roadmap (`docs/ROADMAP2.md`), and the Milestone 16 plan (spec 0107).
- **Verifier-blind-spot specimens** (spec 0110, #122): over-citation passes generic
  containment; containment matches across word boundaries — committed beside the
  existing trigger specimens; ADR 0005 addendum.
- **One-shot preparation** (spec 0111, #123): the public sandbox repo
  (`robert-vetter/tessera-exec-oneshot`), the rewritten DEPLOYMENT runbook
  (verify-the-issue-URL step, labels-silently-dropped note), and the recorded
  Milestone-15 close checklist.

### Changed

- Audit drift repaired (spec 0108, #120): STATUS backfill for the Milestone-15
  sessions, WRITEUP idempotency truth, DEPLOYMENT embeddings row ("built and
  measured on SAP"), README count/pointers, CAPABILITIES future-work markers,
  the `specs/README.md` numbering ledger — plus 68 stale merged remote branches
  pruned.
- **Refuse-kind eval cases are now inside the faithfulness accounting**
  (spec 0110, #122; audit B7) — measured effect on every battery: zero; the
  floor's reach is wider.

### Fixed

- **Trust-path hardening B1–B5 + review findings** (spec 0109, #121): the
  recorder never clobbers the historic receipt (persist only `created`/`exists`,
  refuse-before-network, exclusive-create, case-insensitive guard); the
  idempotency pre-check is **label-independent** (ADR 0026 addendum); the PAT can
  no longer leak via `repr`; fenced log/diff content cannot break out of its
  fence into a real issue and multiline non-fenced values withhold the payload
  (ADR 0024 addendum); `{pr}` path segments pass an allowlist; the real transport
  **refuses redirects** (urllib would forward `Authorization` cross-origin and
  rewrite POST→GET, risking a false `created`).

## [milestone-15] — 2026-07-03

Cross the last honest edge of the execution arc: **actually send** one grounded action —
exactly once, behind approval, best-effort idempotent — and commit the receipt.

### Added

- **Best-effort idempotency on the real execution path** (Unit 2, ADR 0026, #115):
  a deterministic `sha256` idempotency key over the grounded request, a
  three-surface marker (HTML comment + visible footer + `idem-` label), a paging
  pre-send existence check on the primary endpoint, new `exists`/`inconclusive`
  receipt outcomes, and `idempotency_key` on the receipt.
- **Real-execution recorder, scrubber, and runbook** (Unit 3, #116):
  `scripts/record_real_execution.py` (maintainer-only one-shot, never CI),
  `tessera.agent.recording.redact_receipt` (response allow-list + token-like-key
  redaction), the `docs/DEPLOYMENT.md` one-shot runbook, `.env.example`, and the
  `data/execution/` layout.
- **The real send, recorded** (Units 4–5 per spec 0111): the maintainer-approved
  one-shot created
  [`tessera-exec-oneshot#1`](https://github.com/robert-vetter/tessera-exec-oneshot/issues/1)
  from a grounded incident over a real CI failure (run 27014662820) —
  `outcome="created"`, `sent=true`, status 201; the scrubbed `ExecutionReceipt` +
  `MANIFEST` committed under `data/execution/`. The first attempt's 403 (a
  read-only token) exercised the hardened failure path in the wild: receipt
  printed, nothing persisted, non-zero exit, retry unblocked.

### Changed

- The real-execution recorder records **only an approved send** — a rehearsal
  writes nothing (#117).

## [milestone-14] — 2026-07-01

Take the named next step and reach the fourth boundary: from the **executable payload**
(M13) to **effectful execution behind approval**. An enterprise agent can ask Tessera
over MCP to **execute** a grounded action — run by a **simulated actuator that sends
nothing** by default, gated on a fully-grounded payload so **nothing executes over
ungrounded ground** — and receive a lossless `ExecutionReceipt`. A real GitHub actuator
exists as an opt-in seam (double-gated on approval **and** a credential, so `sent=True`
is earned), contract-tested against a fake transport but **its real transport/network
never invoked in CI**. Fully **deterministic, offline, CI-reproducible** (the M8–M13
posture); faithfulness gated at 1.0 throughout, now also **across the execution
boundary**. **Zero frozen-core delta** — the whole milestone is the additive execution
layer plus the thin MCP tool.

### Added

- **The execution layer (ADR 0025).** `tessera/agent/execution.py`: an `Actuator`
  protocol; `SimulatedActuator` (the default — records the exact would-be request and
  sends nothing, transparently synthetic, no fabricated resource id); an opt-in
  `GithubActuator` (stdlib `urllib`, an injected `Transport`, approval + credential
  gated, its real transport/network never invoked in CI); `ExecutionReceipt` (a lossless,
  JSON-serializable trust record); and `execute_action` / `execute_payload` gated on
  `RenderedPayload.all_grounded`.
- **MCP `execute_action` tool (spec 0100).** A thin seventh tool on `tessera-mcp` wired
  to the **simulated** actuator only (the server holds no credential and can never send);
  the committed `data/mcp_session/` session now also runs a simulated create-issue
  execution, a simulated PR-comment execution, and a withheld execution.
- **Trust across the execution boundary (spec 0101).** `tests/test_execution_boundary.py`,
  a CI-gated property over data-derived cases: every simulated execution consumed an
  `all_grounded` payload and its receipt is a lossless record (each slot's verdict
  recomputed independently from the grounding); **faithfulness is 1.0 across the execution
  boundary**; nothing executes over ungrounded ground; the real path sends iff
  approved+credentialed (fake transport).

### Trust properties

- **Nothing executes over ungrounded ground.** Unless the M13 payload is `all_grounded`,
  `execute_action` returns a **withheld** receipt — no request, nothing executed, nothing
  sent. The gate is before dispatch, so it holds for every actuator (the execution
  analogue of "a refusal never becomes an answer").
- **The default sends nothing; a simulation is never dressed as real.** The simulated
  receipt is marked `simulated=True` / `sent=False` and carries no fabricated resource id.
- **`sent=True` is earned.** The real path is double-gated (approval **and** a credential);
  a non-2xx or transport error is an `error`, not a send. Render/simulate ≠ send:
  `{owner}`/`{repo}` stay unbound; nothing leaves this repository.

### Process

- The trust-bearing execution layer carried its **mandated pre-merge adversarial
  multi-agent review** (6 lenses × 9 agents, every finding independently reproduced): **0
  majors**, 3 confirmed findings, all fixed and pinned before merge — the receipt aliased
  the payload's mutable `body` dict (copy-on-inherit); `blocked`/`error` receipts set
  `withheld_reason` while `withheld=False` (reserved that field for the ungrounded gate);
  and "never invoked in CI" **overclaimed** the actuator (it *is* contract-tested in CI
  against a fake transport — only the real transport/network is not), scoped across the
  docstrings, ADR 0025, and the specs.

## [milestone-13] — 2026-06-30

Carry the trust contract one boundary further — from the **action draft** (M12) to the
**executable payload**. An enterprise agent can ask Tessera over MCP to **render the
exact GitHub request** a grounded action would send (a create-issue for an `incident`, a
PR comment for a `pr_summary`) — with every value traced to a verifier-passing field —
and Tessera **sends nothing**. Fully **deterministic, offline, CI-reproducible** (the
M8–M12 posture); faithfulness gated at 1.0 throughout, now also **across the payload
boundary**. **Zero frozen-core delta** — the renderer is additive.

### Added

- **The dry-run payload renderer (ADR 0024).** `tessera/agent/payloads.py`:
  `render_payload(proposal)` / `preview_payload(action, domain, question)` turn a
  verifier-checked `ActionProposal` into a `RenderedPayload` — the exact GitHub wire
  request (method, path, JSON body). Every content value is one verified `ActionField`
  (the issue title, each body section, the `{pr}` resource id); everything else is
  declared scaffolding (section labels, code fences, the fixed issue labels, the unbound
  `{owner}`/`{repo}`), never asserted grounded.
- **MCP `preview_payload` tool (spec 0095).** A thin sixth tool on `tessera-mcp`
  serializing the renderer verbatim; the committed `data/mcp_session/` session now also
  previews a rendered create-issue, a rendered PR comment, and a withheld payload.
- **Trust across the payload boundary (spec 0096).** `tests/test_payloads_boundary.py`,
  a CI-gated property over data-derived cases: every rendered payload is field-grounded,
  lossless, and byte-reconstructable from the verified fields; **faithfulness is 1.0
  across the payload boundary**; a withheld payload carries no request.

### Trust properties

- **Rendered iff `all_grounded`.** A refused / partially-verified / route-incompatible /
  wrong-domain / undeclared-role proposal is **withheld** — no request is ever rendered
  over ungrounded ground (the payload analogue of "a refusal never becomes an answer").
- **render ≠ send.** `sent=False`, `requires_approval=True`; no transport, socket, or
  credential. A human or agent binds `{owner}`/`{repo}` and sends, outside Tessera —
  the honest edge. Effectful execution remains the named next step (ADR 0024).
- **Added-nothing, provably failable.** The wire request is byte-reconstructable from
  the verified fields plus the declared scaffolding; the anti-smuggle check is an
  independent reconstruction (a token smuggled into body, labels, or path fails it).

### Process

- The renderer carried its **mandated pre-merge adversarial multi-agent review** (6
  lenses × 12 agents, every finding reproduced): 0 majors, 4 minors + 2 nits, all fixed
  and pinned before merge — chiefly the `{pr}` resource hardening (select the PR record,
  require a clean segment, else withhold), selecting the subject by role, and replacing
  the subtractive anti-smuggle heuristic with independent reconstruction equality.

## [milestone-12] — 2026-06-30

Extend the trust substrate from **answers to actions**: an enterprise agent can ask
Tessera over MCP to **draft an action** — an `incident` from a root-cause analysis, a
`pr_summary` from a change — and receive a grounded, cited, **field-verified
propose-and-approve proposal**, or a carried refusal. Tessera drafts and verifies;
nothing is executed. Fully **deterministic, offline, CI-reproducible** (the M8–M11
posture); faithfulness gated at 1.0 throughout, now also **across the action boundary**.
**Zero frozen-core delta** — the action layer is additive.

### Added

- **The grounded-action layer (ADR 0023).** `tessera/agent/actions.py`:
  `draft_action(kind, domain, question)` builds an `ActionProposal` strictly from a
  verifier-checked `GroundedResult` (the Milestone-11 boundary). Each `ActionField` carries
  a role, a grounded value (a claim's verbatim text or a verbatim fragment of its cited
  evidence), the inline provenance, and a **recomputed `verified` verdict** — the source
  claim must have passed `is_supported` *and* the value be faithful (per-record normalized
  containment, mirroring the engine's verifier). `all_grounded` is true only when every
  field passes — earned, not tautological (a provably-failable test injects an unsupported
  token and asserts the verdict drops). A small declared catalog: `incident` (from a devex
  or github_actions RCA), `pr_summary` (from a devex change). A refused, route-incompatible,
  or wrong-domain grounding is **carried as a refusal with no fields** — never drafted over.
  Propose-and-approve: `requires_approval=True`, `executed=False`; nothing is executed.
- **MCP action tools (spec 0090).** `tessera-mcp` gains thin `list_actions` and
  `draft_action` tools that only serialize the layer (no drafting logic on the server); the
  SDK stays the opt-in `agent` extra and the no-`mcp`-in-base-graph pin holds. The committed
  `data/mcp_session/` client↔server session now also drafts an incident, a PR summary, and
  carries a refusal.
- **Trust across the action boundary (spec 0091).** `tests/test_actions_boundary.py`, a
  CI-gated property over cases **derived from the data** (every failed run, every PR): each
  drafted action is field-grounded and a **lossless** projection of its grounding (same
  value, support, and verdict per field), and **faithfulness is 1.0 across the action
  boundary**. ADR 0005/0006 re-examined at the boundary and recorded still not forced.

### Changed

- **Router-ambiguity alignment (spec 0088).** The business router now defers a bare
  ambiguous entity term (`"Logistik"`, which ties across two distinct entities under
  `compose`'s own resolver) to the refusing `compose` path, closing the Milestone-11
  router-vs-engine divergence; the `business/05` pin was removed from
  `tests/test_boundary.py` and no battery number moved.

### Trust / process

- A **pre-merge adversarial multi-agent review** of the grounded-action layer (six lenses,
  every finding independently reproduced) caught and fixed a real soundness gap — the field
  check compared the value against *concatenated* evidence, one seam-spanning token weaker
  than the engine's per-record verifier — plus a docstring overclaim, both pinned.
- **Frozen core empty-diff** `milestone-11..HEAD` (ADR 0008): the action layer is additive;
  the only existing-code production change is the vertical-side router fix. Faithfulness
  1.000 on every battery; no battery number moved.

## [milestone-11] — 2026-06-28

Expose Tessera to AI agents over the **Model Context Protocol** as **read-only
grounded tools**, and prove the trust contract survives the protocol boundary — the
project's thesis ("a trust layer for enterprise AI agents") made callable. Fully
**deterministic, offline, and CI-reproducible** — the MCP SDK is an opt-in extra; the
default graph and CI stay pure-stdlib. Faithfulness gated at 1.0 throughout. The one
sanctioned frozen-core delta is the heading-chunk retrieval fix folded in as the
opening unit.

### Added

- **The grounded-tool layer (ADR 0022).** A vertical-neutral `tessera/agent/` package:
  `ground(domain, question)` routes through the deterministic engine over all three
  domains (business, devex, the real github_actions connector) and returns a
  JSON-serializable `GroundedResult` — the routing decision, claims each with a
  per-claim verifier verdict and full provenance inline, and a refusal carried
  explicitly so it can never become an answer across the boundary. A second tool,
  `assertions(domain, record_id)`, surfaces the reversible entity-resolution trail.
- **The MCP server `tessera-mcp`.** A thin transport (no grounding logic) registering
  the read-only tools over the SDK's stdio transport. The SDK is the **opt-in `agent`
  extra** (`uv sync --extra agent`), the hdbcli/`cloud` pattern; the default import
  graph and CI never touch it (a subprocess pin; CI's `uv sync --frozen` is pure-stdlib).
- **A real MCP client↔server session**, captured to `data/mcp_session/` by
  `scripts/record_mcp_session.py` (the no-spend "ran on" artifact): a grounded answer
  per domain, a refusal carried as a refusal, the ER trail — every claim verified.
- **The boundary-trust measurement (`tests/test_boundary.py`).** Over every gold case
  in all three batteries: the boundary projection is lossless (same claims, support,
  verdicts as the engine `Answer`) and **faithfulness is 1.0 across the boundary**.

### Changed

- **A Markdown heading now leads its section (ADR 0021).** `ingestion.chunk_text`
  merges a pure ATX-heading block into the content it introduces, so a heading no
  longer competes with its own clause in BM25 — retiring the Milestone-10 near-tie
  fragility and restoring the renewal retrieval test to a strict top-1 assertion. The
  one sanctioned frozen-core delta this milestone (devex/github chunk ids unchanged —
  their log corpora have no ATX headings; gold ids re-pointed deliberately).
- **`ChatSession` shares the grounded-tool registry + verify loop** (one source of
  truth for the domains and the verifier), with its behaviour pinned byte-identical.

### Measured / recorded

- **Faithfulness 1.0 across the boundary** (the headline, gated in CI); the existing
  battery numbers are unchanged (the agent layer is a consumer, not a new answer path).
- **Two honest router-vs-engine divergences pinned and explained** (neither a
  faithfulness breach): the offline synonymy case the agent path inherits as a refusal
  (only embeddings bridge it; M11 is offline by choice); and the bare term `"Logistik"`
  the production router answers where the eval's `compose` refuses as ambiguous — a
  pre-existing router gap (the chat surface shares it), recorded as the next lever.
- **ADR 0005 (LLM-judge) / 0006 (semantic routing) re-examined and recorded NOT
  forced** at the boundary.

## [milestone-10] — 2026-06-28

Add a **registration key** (`VATRegistration`) as the most decisive entity-resolution
field, closing the one floor multi-field name+address ER (Milestone 9) could not reach:
two genuinely distinct firms with the **same name AND the same address**. Fully
**offline and CI-reproducible** — no embedding, no cloud. Faithfulness gated at 1.0
throughout. The Milestone-9 engine already supported it, so this milestone makes **no
engine logic change** — the smallest of the three frozen-core deltas.

### Added

- **Registration-key entity resolution (ADR 0020).** The exact legal-entity identity
  key slots into the existing Milestone-9 gate as the **first** (most decisive)
  `match_field`: `CUSTOMER_MATCH_FIELDS = ("vat_registration", "postal_code",
  "city_name")`. Exact normalized equality (the structured key is matched exactly, not
  by a fuzzy ratio); it decides above the address, so same name + same address +
  different key → split, and (a free consequence) a same-key pair survives a postal
  disagreement, retiring Milestone 9's "postal-anchored" cost.
- **`VATRegistration` on every `I_Customer` row**, assigned per legal entity
  (duplicates share one VAT; distinct firms differ; a hash collision between distinct
  seeds is a loud build failure). Existing columns byte-identical; the address master
  and MANIFEST counts unchanged in this step.
- **A same-name/SAME-address disambiguation pair** (two distinct "Havel Kontor GmbH"
  firms at one address, distinct VATs), appended outside the RNG stream. The new gold
  case (kind=refuse) is the **measured before/after**: name + address ER over-merges and
  wrongly answers the ambiguous-name question (business gold quality **0.909**); the
  registration key splits the firms and correctly refuses (**1.000**) — both points in
  `eval/history.jsonl`, CI-reproducible.

### Changed

- **`build_demo_graph` defaults to the key-first `CUSTOMER_MATCH_FIELDS`;
  `sources/salt.py`** denormalizes the key onto the customer's address node (a shared
  address carries none — absence is never a contradiction). The resolved clusters are
  byte-identical to the Milestone-9 address-only path except the one intended Havel
  split (pinned, not assumed). Business gold 10 → 11, synthetic 53, every metric 1.0.
- **`graph.py` bridge reason** generalized from "bridged by address" to "bridged by
  corroborating field" (`signal.detail` names the actual field) — an honesty fix so a
  key-bridged merge does not misreport the field. Behaviour-preserving; clusters
  unchanged.
- **`test_renewal_question_returns_the_actual_renewal_clause`** relaxed to a robust
  top-2 invariant: adding 4 short records shifted BM25 `avgdl` and flipped a 0.05%
  near-tie (a section heading vs its first clause, both surfaced from the MSA with
  doc-span provenance). The eval floor is untouched; the heading-chunk root cause is
  filed as retrieval future work.

### Notes

- **Third sanctioned frozen-core delta** (after Milestones 8–9): `graph.py` only (a
  one-line wording generalization), `resolution.py` empty-diff. The key reuses the M9
  exact-equality gate; the schema knowledge stays in the source (ADR 0011 pattern).
- **Pre-merge adversarial review** (5 lenses, 8 agents): 3 findings, 0 majors, all
  fixed (a real-SALT-safe denormalization guard; finishing the field-general wording).
- **New floor recorded:** two distinct firms with the same name **and** address **and**
  key are indistinguishable from the data — only an external registry separates them.

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

[Unreleased]: https://github.com/robert-vetter/tessera/compare/milestone-17...HEAD
[milestone-17]: https://github.com/robert-vetter/tessera/compare/milestone-16...milestone-17
[milestone-16]: https://github.com/robert-vetter/tessera/compare/milestone-15...milestone-16
[milestone-15]: https://github.com/robert-vetter/tessera/compare/milestone-14...milestone-15
[phase-4]: https://github.com/robert-vetter/tessera/compare/phase-3...phase-4
[phase-3]: https://github.com/robert-vetter/tessera/compare/phase-2...phase-3
[phase-2]: https://github.com/robert-vetter/tessera/compare/phase-1...phase-2
[phase-1]: https://github.com/robert-vetter/tessera/compare/phase-0...phase-1
[phase-0]: https://github.com/robert-vetter/tessera/releases/tag/phase-0
