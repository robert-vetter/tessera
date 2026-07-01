# 0103. Milestone 15 plan: actually sending behind approval + engineered idempotency

- **Phase / milestone:** Milestone 15 — Cross the last honest edge of the execution
  arc: **actually send** one grounded action from this project (the first real,
  credentialed, irreversible external side effect), behind approval — and make the real
  path **honestly idempotent** so a re-run does not silently duplicate. Two parts, in
  order: (a) engineer best-effort client-side idempotency on the opt-in `GithubActuator`
  as the **CI-verifiable core** (deterministic, offline, faithfulness gated 1.0, frozen
  core untouched); then (b) a **single maintainer-triggered real send** — a grounded
  incident create-issue from a *real* Tessera CI failed run into a *new sandbox repo* —
  recorded as a scrubbed real `ExecutionReceipt`, the "ran on X" analogue of M6/M7 for
  the execution boundary. Post-roadmap (ROADMAP `phase-0`…`phase-4`; hardening
  `milestone-5`; embeddings-on-SAP `milestone-6`; embeddings-beyond-retrieval
  `milestone-7`; deterministic-ER-precision `milestone-8`; name+address ER `milestone-9`;
  registration-key ER `milestone-10`; agentic/MCP read-only `milestone-11`; grounded
  actions over MCP `milestone-12`; dry-run payload preview `milestone-13`; effectful
  execution behind approval `milestone-14`).
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018: decisions recorded here instead
  of asked — except the project-shaping scope questions below, which were asked and
  answered 2026-07-01)

## Problem

Through fourteen milestones the trust substrate climbed one measured boundary at a time —
grounded **answers** (M11) → grounded **action drafts** (M12) → the **executable
payload** (M13) → **effectful execution behind approval** (M14) — and each was
faithfulness-gated 1.0 with an empty frozen-core diff. M14 built the opt-in
`GithubActuator` (double-gated on approval **and** credential, pure-stdlib `urllib`, an
injected transport, contract-tested against a fake transport) and proved the real path
is *real* — it binds, authenticates, and would send. But it deliberately stopped one
step short: **nothing has ever actually been sent from this repository.** The M14 STATUS
close and ADR 0025 record this as *the* honest edge, and name the follow-through
precisely: *"actually sending — a maintainer-authorized real GitHub one-shot — is the
named next posture step, deliberately not taken (credentialed and irreversible). A real
create-issue is not idempotent; recorded as a caller responsibility, not engineered."*

M15 takes exactly that step, and closes the idempotency edge that comes with it. This is
the biggest posture decision the project has faced — the first time a side effect leaves
the machine — so its two project-shaping halves (whether to send at all, and where) were
**asked and answered**, and the honest way to build it is the M6/M7 structure the
project already established: a **CI-verifiable offline core** (here: engineered
idempotency, contract-tested against a fake transport, nothing sent) plus **one recorded
online run** (here: the single real create-issue), with CI staying offline and the
default reverting to the simulated actuator.

**Maintainer decisions (asked & answered 2026-07-01 — project-shaping, so asked):**

1. **The thrust — actually send behind approval + engineered idempotency.** Chosen over
   a second execution target (Jira create-issue), idempotency-only (harden without
   sending), and SAP platform work (HANA graph persistence / BTP serving). It is the
   named M14 follow-through and the thesis-completing move: a "trust layer for enterprise
   AI agents" that, for the first time, actually *acts* — with the act made safe to
   repeat. It carries **ADR 0026** (the idempotency mechanism and its honest limits).
2. **The destination — a new sandbox repo.** The single real side effect lands in a
   fresh throwaway repo the maintainer creates (e.g. `robert-vetter/tessera-exec-oneshot`),
   not the live Tessera repo and not an existing project. Chosen to contain the blast
   radius: a duplicate or an unwanted issue there is harmless and reversible. The issue's
   *content* is grounded in Tessera's real CI data; the destination is a deployment
   binding, not evidence.
3. **The trigger & credential — the maintainer runs the one-shot; the credential never
   enters the agent's environment.** The agent builds and proves the entire path green
   offline (against a fake transport); the **maintainer** performs the single real send
   with their own least-privilege fine-grained PAT sourced from a gitignored `.env`, and
   pastes back a sanitized receipt. Chosen over authorizing the agent to run it with a
   supplied token: it keeps the credential entirely out of the session.
4. **The content — a real `github_actions` incident create-issue.** The one real issue is
   a grounded incident RCA over a *real* Tessera CI failed run (already in the committed
   `data/github_actions/` snapshot), chosen over the synthetic DevEx corpus (whose ids
   are `PR-NNN`/`R-NNNN`) and over a PR comment (which needs an existing open PR). Real
   grounded content + a real send is the strongest, most honest pairing.

**Finer decisions (not project-shaping — decided and recorded here, per autonomous
mode), grounded in the design pass (`specs/` companion notes; ADR 0026):**

- **Best-effort, not exactly-once — stated everywhere.** GitHub's `POST
  /repos/{owner}/{repo}/issues` has no server-side idempotency key, and the search index
  is eventually consistent (a just-created issue takes ~1 min+ to be findable). So the
  engineered mechanism is honestly **best-effort client-side idempotency**, not a
  correctness guarantee; the residual duplicate window (a retry inside the indexing lag)
  is documented as a known limit in ADR 0026, the spec, STATUS, and the WRITEUP — never
  papered over.
- **A deterministic idempotency key + a three-surface marker.** Inside
  `GithubActuator.execute`, after both gates pass and before the POST, compute
  `key = sha256(canonical_json({method, path, body}))` over the grounded request with the
  marker **excluded** from the hashed body (so the key never depends on itself). Stamp one
  hash onto the outgoing issue in three derived surfaces: an HTML comment
  `<!-- tessera-idempotency-key: sha256:<hex> -->` in the body (primary `in:body` search
  target, invisibly rendered), a human-visible provenance footer line, and a
  deterministic `idem-<first16hex>` label (an index-independent handle).
- **A pre-send existence check that refuses rather than duplicates.** Before the POST,
  a new `Transport.get()` runs the lag-prone `GET /search/issues?q=…"tessera-idempotency-key:
  sha256:<hex>"…` **backed by** an index-independent `GET
  /repos/{owner}/{repo}/issues?labels=idem-<hex>&state=all` (the primary datastore, not
  stale). If either returns a candidate whose body is verified client-side to contain the
  exact marker substring, short-circuit to a new `outcome="exists"` (`sent=False`, the
  existing issue's scrubbed number/url carried). If the pre-check is **inconclusive**
  (`incomplete_results:true`, a search 403/429 rate-limit, or a fuzzy hit failing exact
  verification), return `outcome="inconclusive"` (`sent=False`) — **never silently
  create** (a correct refusal beats a confident duplicate; the groundedness principle
  applied to a side effect). Otherwise proceed to the POST (`outcome="created"`) with the
  marker embedded, so the *next* run dedupes.
- **The marker is deployment-time scaffolding the real actuator adds at send, recorded in
  the real receipt.** It never enters the M13 renderer or the grounded slots — exactly
  like the existing `created`-path `{owner}/{repo}` rebinding, which the real actuator
  already records instead of the raw payload path. Consequences: the M13 renderer, the
  grounded slots, `test_payloads_boundary.py`, and the *simulated* execution boundary
  (`test_execution_boundary.py`) are **unaffected** — the marker exists only on the real
  `GithubActuator` path; **faithfulness stays gated at 1.0** across every boundary the
  repo measures. The real receipt records the marker-augmented body it actually POSTed
  (lossless wrt what was sent), and the new contract tests pin the marker/dedup behavior
  against the fake transport.
- **A read method on the Transport seam.** The M14 `Transport` is `post()`-only, so a
  pre-send GET cannot be expressed. Extend the `Transport` Protocol with
  `get(url, *, headers) -> tuple[int, dict]`, implement it on `_UrllibTransport` behind
  `# pragma: no cover - real network, never in CI`, and add it to every fake transport.
- **`idempotency_key` on the receipt.** `ExecutionReceipt` gains an optional
  `idempotency_key` field (populated on the real path, `None` for the simulated dry run),
  surfaced in `to_dict()` so every real receipt is self-identifying and auditable. This
  ripples through `to_dict()` to the MCP `execute_action` handler output, so the committed
  `data/mcp_session/` artifact is **regenerated mechanically** (the field is `None` on the
  simulated path; the handler-==-`to_dict()` contract test still holds; the MCP surface
  stays simulated-only and holds no credential — no new capability there).
- **A genuine one-shot; the default reverts to simulated.** The real send runs once, by
  the maintainer, into the sandbox repo; the scrubbed receipt is committed; the default
  everywhere the repo runs stays `SimulatedActuator`; CI stays offline. No standing live
  path is wired.
- **No new dependency, no pip extra, no MCP change.** The idempotency work is pure-stdlib
  `urllib` + `hashlib`/`json` on the additive `agent/execution.py` layer. The MCP server
  still wires the simulated actuator only and holds no credential.

## The design (recorded for ADR 0026)

**Idempotency is a strict addition to the opt-in real path only; the verifiable core and
the grounded payload are unchanged.** All code lands in the additive
`src/tessera/agent/execution.py` (ADR 0025 established this layer is *not* ADR 0008 frozen
core). The mechanism:

1. **Key derivation.** `idempotency_key(payload) = "sha256:" + sha256(canonical_json(
   {method, path, body}))`, where `canonical_json` sorts keys, uses fixed separators, is
   UTF-8, and hashes the grounded body **without** the marker. A pure function of grounded
   intent.
2. **Marker embedding** (real path, at send): the HTML comment in `body["body"]`, the
   visible footer line, and the `idem-<first16hex>` label in `body["labels"]`. Declared
   scaffolding — a deterministic function of already-verified values (like the fixed M13
   labels/headings), asserting no new claim.
3. **Pre-send existence check** (real path, after gates, before POST): search + primary
   cross-check + exact client-side marker verification → `exists` | `inconclusive` |
   proceed.
4. **Outcomes.** `ExecutionReceipt.outcome` gains `"exists"` and `"inconclusive"`
   (both `sent=False`, `executed=False`, `simulated=False`, `withheld=False`, detail in
   `result`), beside the M14 `withheld`/`simulated`/`created`/`blocked`/`error`.
   `withheld_reason` stays reserved for the ungrounded M13 gate. `idempotency_key` is added
   to the dataclass + `to_dict()`.
5. **Transport.** `Transport.get` added to the Protocol + `_UrllibTransport` (pragma
   no-cover); fake transports gain `get` + an `existing` toggle + a `gets` record.

**Honest properties preserved (the trust *extension*, not a new write surface):**

- **Nothing executes over ungrounded ground** — the M13/M14 `all_grounded` gate in
  `execute_payload` is unchanged; idempotency runs only *inside* the real actuator, on an
  already-grounded payload.
- **`sent=True` is still earned** — approval **and** credential, unchanged; idempotency
  adds a *third* reason a real send may not happen (`exists`/`inconclusive`), never a
  reason it happens more easily.
- **Faithfulness stays 1.0 across every boundary** — the marker is real-path-only
  scaffolding; the simulated path, the renderer, and the grounded slots are untouched.
- **Deterministic, offline, pure-stdlib on the verifiable core** — the leak-guard still
  holds; the simulated path opens no socket; the real GET/POST are pragma-no-cover and
  never run in CI.

**The recorded real run** (Unit 4) mirrors the M6/M7 offline-eval + one-recorded-online
structure: a new `scripts/record_real_execution.py` (a sibling of
`scripts/record_mcp_session.py`, **not** run in CI) constructs
`GithubActuator(owner, repo, token, …)` and calls `execute_action(..., approve=True)`
over a real failed run; the maintainer runs it with a PAT from a gitignored `.env`; the
scrubbed receipt is committed under `data/execution/` with a `MANIFEST.json`
(`"synthetic": false`, `fetched_by`, a fixed recorded date). Scrubbing redacts
`result["response"]` (tokens/ids → `***`, drop volatile url/html_url per the snapshot
precedent); the PAT is safe by construction (the `Authorization` header is built locally
and never enters the receipt). gitleaks (pinned, enforced in pre-commit and CI) is the
final gate on the committed artifact.

## Success criterion

Tessera **actually sends** one grounded action — recorded, scrubbed, and honest — for
the first time, and its real path is **best-effort idempotent**, proven offline in CI:

- **Engineered idempotency, contract-tested offline.** `GithubActuator` computes a
  deterministic key, embeds the three-surface marker, runs the pre-send check, and returns
  `created` (no prior issue), `exists` (marker found → `sent=False`), or `inconclusive`
  (pre-check undecided → `sent=False`, never a silent duplicate) — pinned in the same
  "iff" style as the M14 send test, against an injected fake transport, real network never
  touched. Faithfulness stays 1.0 across every boundary; no battery number moves.
- **One recorded real send.** A single maintainer-run one-shot creates one real issue in
  the sandbox repo (`sent=True`, `outcome="created"`, the marker embedded so an immediate
  re-run returns `exists`); the scrubbed real `ExecutionReceipt` is committed under
  `data/execution/`, recorded in STATUS + the WRITEUP in the honest M6/M7 "ran on X"
  before/after style. No secret is committed (gitleaks green).
- **The default and CI stay offline.** The default actuator everywhere the repo runs is
  the simulated one; the real transport/network is never invoked in CI; the MCP surface
  stays simulated-only and holds no credential.
- **Zero frozen-core delta.** The ADR 0008 empty-diff audit over `milestone-14..HEAD`
  (the corrected post-relocation path list) is empty; all new work is the additive
  `agent/execution.py` + `scripts/` + `docs/` + `data/` + tests + specs + ADR 0026.

## Acceptance criteria

- [ ] **Phase plan (Unit 1, spec 0103).** This plan + the four recorded scope decisions
      (asked 2026-07-01) + the finer decisions + the design for ADR 0026.
- [ ] **Idempotency on `GithubActuator` + ADR 0026 (Unit 2, spec 0104).** The deterministic
      key, the three-surface marker, `Transport.get`, the pre-send existence check with
      exact client-side verification, the new `exists`/`inconclusive` outcomes, and
      `idempotency_key` on the receipt — additive on `agent/execution.py`, pure-stdlib.
      New fake-transport contract tests for `created` (marker embedded) / `exists` /
      `inconclusive`; leak-guard still green; faithfulness 1.0 across the boundary
      unchanged. **ADR 0026** records the mechanism, the best-effort (NOT exactly-once)
      honesty caveat, the search eventual-consistency residual, and the refuse-don't-
      duplicate policy. **Mandated pre-merge adversarial multi-agent review** (a
      trust-bearing change to the surface that can cause a side effect).
- [ ] **Runbook + recorded-receipt plumbing (Unit 3, spec 0105).** `scripts/record_real_execution.py`
      (sibling of `record_mcp_session.py`, not in CI) + its scrubber, green offline against
      a fake transport; a `docs/DEPLOYMENT.md` runbook section (create the sandbox repo,
      mint the least-privilege PAT, `.env` handling, the exact one-shot command, the
      paste-back-and-commit flow); `data/execution/` layout + `MANIFEST.json`;
      `.env.example`/`.gitignore` reviewed; the receipt-field ripple regenerates
      `data/mcp_session/` (handler-==-`to_dict()` contract test still green).
- [ ] **The real send + record (Unit 4, spec 0106).** The maintainer runs the one-shot;
      the scrubbed real `ExecutionReceipt` is committed under `data/execution/`; STATUS +
      WRITEUP get the honest "recorded online run" entry; the `tessera-eval --record` point
      (if any) is appended as a timestamped, non-CI-reproducible measurement with
      faithfulness held 1.0. Default reverts to simulated; MCP untouched.
- [ ] **Close (Unit 5, spec 0107).** Gate green under multiple `PYTHONHASHSEED` values;
      WRITEUP "actually sending behind approval" section (the real send + the idempotency
      mechanism + its honest limits); README (the corrected scope: Tessera has now sent
      once, recorded; the real path is best-effort idempotent; default simulated);
      CHANGELOG `[milestone-15]`; ADR 0026 nav + index; the ADR 0008 **empty-diff core
      audit** run and confirmed empty; STATUS; tag `milestone-15`; memory; next-milestone
      kickoff handed back.

## Scope

**In — the unit breakdown (one PR each, spec each):**

| Unit | Spec | Content |
|---|---|---|
| 1 | 0103 | this plan + the four recorded scope decisions (asked 2026-07-01) + finer decisions + the design for ADR 0026 |
| 2 | 0104 | idempotency on `GithubActuator` — deterministic key, three-surface marker, `Transport.get`, pre-send existence check, `exists`/`inconclusive` outcomes, `idempotency_key` on the receipt; fake-transport contract tests; leak-guard green; **ADR 0026**; **adversarial review** |
| 3 | 0105 | `scripts/record_real_execution.py` + scrubber (green offline); `docs/DEPLOYMENT.md` runbook; `data/execution/` + `MANIFEST.json`; `.env`/gitignore review; regenerate `data/mcp_session/` for the receipt-field ripple |
| 4 | 0106 | the single maintainer-triggered real send; committed scrubbed real receipt; STATUS + WRITEUP recorded-online entry; optional `--record` timestamped point |
| 5 | 0107 | close: WRITEUP/README/CHANGELOG/STATUS, ADR nav/index, empty-diff core audit, tag `milestone-15`, memory, kickoff |

**Out (explicitly):**

- **Exactly-once / server-side idempotency.** GitHub offers none for `POST /issues`;
  M15 engineers **best-effort** client-side idempotency and states the residual
  duplicate window (search-index lag) plainly. Not a correctness guarantee.
- **A standing live real path.** The real send is a single, maintainer-triggered
  one-shot into a sandbox repo; the default reverts to `SimulatedActuator`; no live
  actuator is wired for repeat use.
- **The MCP surface being able to send.** Unchanged from M14: the `execute_action` MCP
  tool wires the simulated actuator only; the server holds no credential. The receipt-field
  ripple regenerates the committed session but adds no send capability.
- **A second target system (Jira) or a multi-target actuator.** One target: GitHub, via
  the M13 renderer. Future work.
- **An LLM anywhere on the execution/idempotency path.** The key, the marker, and the
  pre-send decision are deterministic. ADR 0005/0006 triggers re-examined at the real
  path and recorded not forced.
- **Embeddings / the M6–M7 cloud regime.** Untouched. The only network touchpoint is the
  single real GitHub one-shot (maintainer-run, out of CI).
- **A new gated eval metric.** Faithfulness stays the single hard CI floor at 1.0; the
  idempotency behavior is pinned by contract tests, and the real send is a timestamped
  recorded measurement, not a CI-reproducible gate (the M6/M7 pattern).
- **A frozen-core change.** M15 expects a zero-line frozen-core delta; if one proves
  necessary it gets its own ADR and a pre-merge review (none is anticipated).

## Eval impact

- **Faithfulness — held at 1.0, unchanged.** The idempotency marker is real-path-only
  deployment scaffolding and never touches the renderer or the grounded slots, so the
  payload boundary and the simulated execution boundary measure exactly as in M13/M14.
  The new contract tests pin the real-path dedup behavior; no faithfulness number moves.
- **Coverage / quality — unchanged.** No new answer path; the batteries' numbers must not
  move (proven at close, not assumed).
- **The real send is a recorded, timestamped measurement — not a CI gate.** Like the
  M6/M7 online HANA numbers, the single real `ExecutionReceipt` is recorded honestly
  (faithfulness 1.0 across the boundary it consumed) and is explicitly **not**
  CI-reproducible. CI stays offline.

## Risks / open questions

- **Search eventual-consistency → a residual duplicate window.** A retry inside the
  ~1 min+ search-index lag can still create a duplicate. Mitigated by the
  index-independent `labels=idem-<hex>` cross-check (primary datastore, not stale) and by
  restricting the real send to a throwaway sandbox repo; documented as a **best-effort,
  not exactly-once** limit in ADR 0026 / STATUS / WRITEUP, never as a guarantee.
- **Inconclusive pre-check must refuse, not duplicate.** `incomplete_results:true`, a
  search 403/429, or a fuzzy hit failing exact marker verification → `outcome="inconclusive"`,
  `sent=False`. Pinned by a contract test; recorded as policy in ADR 0026.
- **Credential leakage.** The PAT stays in a gitignored `.env`, is run only by the
  maintainer, and never enters the agent's environment; the token is safe by construction
  in the receipt (the `Authorization` header is built locally, never serialized); the
  recorder scrubs `result["response"]`; gitleaks is the final committed-artifact gate.
- **Non-idempotent race despite the pre-check.** Two concurrent runs, or a retry before
  indexing, could duplicate. Blast radius contained to the sandbox repo; run once, by the
  maintainer; the embedded marker makes an immediate re-run return `exists` (idempotency
  demonstrated on the record); residual race documented, not asserted away.
- **Frozen core / faithfulness perturbation.** All changes confined to the additive
  `agent/execution.py` + `scripts/` + `docs/` + `data/`; the marker treated as declared
  scaffolding excluded from the M13 reconstruction. The Unit 5 close runs `git diff
  milestone-14..HEAD` over the **corrected** frozen path list (note: ADR 0008 originally
  listed `eval/synthetic.py`, relocated by the 0008 Addendum into `business/synthetic.py`
  + `devex/synthetic.py`; `eval/synthetic.py` no longer exists and is **not** in the audit
  command) and records it empty before tagging.
- **Adversarial review scope (Unit 2).** The review must probe specifically: a key that
  depends on itself (marker leaking into the hashed body); the marker smuggling an
  unverified value into the receipt / breaking the M13 reconstruction; a pre-check that
  treats inconclusive as "not found" and duplicates; `exists`/`inconclusive` receipts that
  misreport `sent`/`executed`/`withheld`; and any path where the idempotency logic could
  let `sent=True` happen without approval+credential on a grounded payload.
