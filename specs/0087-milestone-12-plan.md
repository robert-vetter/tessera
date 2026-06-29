# 0087. Milestone 12 plan: grounded actions over MCP (propose-and-approve)

- **Phase / milestone:** Milestone 12 — Grounded actions over MCP: let an agent
  ask Tessera to *draft an action* (open an incident from an RCA, draft a PR
  summary) and receive it as a **grounded, cited, verifier-checked proposal** a
  human/agent approves — Tessera never executes. Post-roadmap (ROADMAP phases
  complete and tagged `phase-0`…`phase-4`; hardening `milestone-5`;
  embeddings-on-SAP `milestone-6`; embeddings-beyond-retrieval `milestone-7`;
  deterministic-ER-precision `milestone-8`; multi-field name+address ER
  `milestone-9`; registration-key ER `milestone-10`; agentic/MCP read-only
  grounded mode `milestone-11`)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018: decisions recorded here
  instead of asked — except the three project-shaping scope questions below, which
  were asked and answered 2026-06-29)

## Problem

Milestone 11 gave Tessera a read-only agentic/MCP surface and **measured the trust
contract across the protocol boundary** (`tests/test_boundary.py`: faithfulness 1.0,
lossless projection, refusals preserved). The M11 close fixed the README's
reverse-overclaim to read: *read-only MCP exists; grounded **actions** are next.* The
WRITEUP's deferred-work section names the same lever — "grounded actions, not just
answers." M11 deliberately scoped *out* effectful actions and action *proposals*
("Tessera is the agent's evidence oracle, not its actuator"), recording them as the
explicit next step in ADR 0022.

Milestone 12 takes that named lever. The thesis is "a trust layer for **enterprise AI
agents**." Through eleven milestones the trust substrate — grounded claims, claim-level
provenance, a deterministic verifier gated at faithfulness 1.0 — has only ever produced
**answers**. An agent that must *act* (file the incident this RCA describes, post the
summary of this PR) currently gets evidence and must compose the action itself,
ungrounded, outside Tessera's guarantee. M12 extends the *same* trust substrate to the
*action draft*: an action a Tessera tool proposes is a structured object whose **every
field traces to verifier-passing evidence**, or it is not proposed at all.

The ER lever is **spent** (M10 residual is registry-only); the agentic dimension M11
opened is the live frontier. This is the natural, in-scope follow-through — and, kept
deterministic, it holds the determinism line the project has held since M8.

**Maintainer decisions (asked & answered 2026-06-29 — project-shaping, so asked):**

1. **The thrust — grounded actions over MCP.** Chosen over router-ambiguity alignment
   alone (folded in here as one unit), a second real connector (Jira), HANA graph
   persistence, and BTP serving. It is the named M11 follow-through and extends the
   trust substrate from answers to actions — the one dimension M11 left open.
2. **Posture — deterministic, no spend.** Proposal fields are composed/templated from
   cited evidence and verifier-checked; **no LLM on the trust path, no cloud, no spend.**
   Fully CI-reproducible (the M8–M11 posture). LLM-narrated drafts (ADR 0013) and
   fully-LLM-drafted actions (the ADR 0005/0006 triggers) were the offered alternatives;
   both declined for M12. The triggers are re-examined at the action boundary and
   recorded as **still not forced**.
3. **Action scope — propose-and-approve only; nothing executed.** A tool returns a
   grounded, cited, verifier-checked **proposal**; a human/agent approves and acts
   *outside* Tessera. Tessera writes nothing, calls no external system, drafts nothing
   for execution. "Propose + dry-run payload preview" and "propose + real execution"
   were the offered alternatives; both declined (real execution is effectful /
   credentialed / irreversible — out of the honest scope of a trust layer). Recorded as
   future work in ADR 0023.

## The design (recorded for ADR 0023)

**An action proposal is a grounded artifact, built strictly from a `GroundedResult`.**
The trust substrate already produces, for any question, a verifier-checked
`GroundedResult` (M11, `tessera.agent.grounded`): a route, ordered claims each with a
boundary `is_supported` verdict and inline provenance, and a refusal carried explicitly.
M12 adds a *consumer* of that object — a **drafter** that maps a `GroundedResult` into an
`ActionProposal` — and never reads raw text, never invents content, never grounds a
second way. Three honest properties make it a trust extension, not a new attack surface:

1. **Drafted only from verifier-passing claims.** A drafter may only *select* among the
   grounded result's claims and *place their verbatim text* (or a labeled concatenation
   of cited fragments) into named fields. Each `ActionField` cites the claim(s)/evidence
   it drew from; a field introduces **no token absent from its cited evidence** (the same
   `normalize()`-containment discipline the verifier uses). Field-grounding therefore
   *reduces to* claim-faithfulness — already gated at 1.0 — plus a "added nothing" check.
   It is **provably failable** (a test injects a field with an unsupported token and
   asserts `verified=False`), so a fully-grounded proposal is earned, not tautological.
2. **A refusal upstream is carried, never drafted over.** If grounding refused (an RCA on
   a run that *passed*, an unknown run, an out-of-scope question), or routed to a path
   incompatible with the requested action kind, the proposal is **not** built: the
   refusal is carried so *an action is never proposed on ungrounded ground* — the
   action-level analogue of M11's "a refusal never becomes an answer."
3. **Propose-and-approve, stated in the contract.** The serialized proposal declares
   `requires_approval: true` and `executed: false`; Tessera performs no side effect. The
   honest edge — that the agent must still decide and act *outside* Tessera — is named in
   ADR 0023 and the WRITEUP.

**The action catalog (small, declared, read-only).** Two kinds, each mapping cleanly from
an existing engine output (no new answer path):

- **`incident`** — drafted from a `devex`/`github_actions` **RCA** grounding
  (`route_kind == "rca"`, `tessera.devex.rca`): fields like `title`, `summary`,
  `failing_run`, `error`, `recurrence`, `linked_incident`, `proposed_fix` — each a
  selection of the RCA's grounded claims. **No invented judgment fields** (no severity,
  no priority — those are not in evidence; their absence is the honest boundary).
- **`pr_summary`** — drafted from a `devex` **change-summary** grounding
  (`route_kind == "summary"`, `tessera.devex.summaries`): fields like `title`,
  `change_summary` (the diff hunks), `motivating_ticket` — each traced; a PR that names
  no ticket yields a proposal without that field (honest omission, as the engine does).

**Where it lives.** `src/tessera/agent/actions.py` (new; *not* in the ADR 0008 frozen
core — additive). The MCP server (`tessera.agent.mcp_server`) gains two thin tools —
`list_actions` and `draft_action` — transporting the layer; the SDK stays the opt-in
`agent` extra; the default import graph stays free of `mcp` (the M11 pins hold). The
action layer is pure-stdlib and **pulls no embedding/LLM/`hdbcli`/`mcp` import** (the
leak-guard is extended). The verifier (`eval/metrics.py`), `graph.py`, `resolution.py`,
and `ingestion.py` are **untouched** — M12 expects a **zero-line frozen-core delta**
(cleaner than M11, which had the sanctioned heading-chunk change).

**The folded-in unit — router-ambiguity alignment (business/05).** `tests/test_boundary.py`
pins a router-vs-engine divergence: the eval's `compose` engine refuses the bare term
*"Logistik"* as ambiguous (it ties across Müller Logistik and Nordwind Logistik), while
the production business **router** routes a bare term to lexical lookup and grounds.
Aligning the router so a bare term that resolves ambiguously (ties across ≥2 distinct
entities under `compose`'s own `resolve_entity`) routes to the refusing compose path
closes the divergence deterministically. It is **vertical-side** (`tessera/business/
routing.py`), not frozen core, but it is a precision/recall risk (over-refusing a
legitimate single-term lookup), so it carries a **pre-merge adversarial review** and a
proof that no battery number moves.

## Success criterion

An enterprise AI agent can ask Tessera over MCP to **draft an action** and receive a
grounded, cited, verifier-checked **proposal** — or a carried refusal — for the DevEx
and real `github_actions` domains, offline and in CI:

- A real MCP client session against `tessera-mcp` drafts an **incident** from an RCA and
  a **PR summary** from a change-summary, each field carrying provenance and a verifier
  verdict, plus a **carried refusal** for an action requested on insufficient/incompatible
  grounding — recorded as a committed transcript (the "ran on" honesty, no spend), the way
  the M11 MCP session is committed.
- **Every field of every drafted action is field-grounded** (cites ≥1 verifier-passing
  claim and adds no unsupported content) and the projection is **lossless** w.r.t.
  verification — measured over representative cases (a pinned CI test, the M11
  boundary-equivalence pattern), so the new capability's effect on the metric is *known*
  (principle 3).
- **A refusal/incompatible grounding never becomes a drafted action** — pinned by a test.
- **The default clone-and-run + CI stay pure-stdlib** — the no-`mcp` import pin still
  holds; the action layer adds no embedding/LLM/MCP import toward the verifier (leak-guard
  extended). Faithfulness stays the single hard gate at 1.0 on every battery.
- **The router-ambiguity divergence is closed** — `business/05` routes to a refusal
  matching its gold kind; the pinned divergence is removed from `tests/test_boundary.py`;
  no battery number moves (proven, not assumed).
- **Zero frozen-core delta** — the ADR 0008 empty-diff audit over `milestone-11..HEAD`
  is empty (the action layer is additive; the router fix is vertical-side).

## Acceptance criteria

- [ ] **Router-ambiguity alignment (Unit 2, spec 0088).** The business router refuses a
      bare ambiguous entity term (`"Logistik"`) as ambiguous, matching `compose`;
      deterministic; the `business/05` pin removed from `tests/test_boundary.py`; a
      targeted test pins both the new refusal and that a legitimate single-term lookup
      still grounds; **no business gold/synthetic number moves** (proven). **Pre-merge
      adversarial review** (precision/recall risk on a shared production router).
- [ ] **Grounded-action layer (Unit 3, spec 0089, ADR 0023).** `src/tessera/agent/
      actions.py` — `ActionProposal`/`ActionField` + the declared `incident` and
      `pr_summary` drafters, built strictly from a `GroundedResult`, **field-grounded and
      verifier-checked at the boundary**, refusals/incompatible-grounding carried,
      JSON-serializable, `requires_approval`/`executed` in the contract. Provably-failable
      field check (adversarial test). Leak-guard extended. Full stdlib coverage. **ADR
      0023** records the grounded-action boundary (propose-and-approve, deterministic,
      field-grounded, nothing executed) + the rejected scopes (LLM-drafted; dry-run
      payload; real execution). **Pre-merge adversarial review** (the new trust-bearing
      surface).
- [ ] **MCP action tools (Unit 4, spec 0090).** `list_actions` + `draft_action` on
      `tessera-mcp` — thin transport, no drafting logic; the no-`mcp`-in-base-graph pin
      still holds; contract test of the wiring; a **committed real MCP client↔server
      session** drafting an incident + a PR summary + a carried refusal.
- [ ] **Trust across the action boundary (Unit 5, spec 0091).** A pinned CI test
      (`tests/test_actions_boundary.py`): over representative RCA/summary cases, every
      drafted action is field-grounded + lossless; an upstream refusal yields a carried
      refusal, never a draft; faithfulness stays the single gate. ADR 0005/0006
      re-examined at the action boundary and recorded **still not forced**.
- [ ] **Close (Unit 6, spec 0092).** Gate green under multiple `PYTHONHASHSEED` values;
      WRITEUP "grounded actions over MCP" section (the drafter, the field-grounding
      measurement, the propose-and-approve scope + deferred execution, the still-live
      triggers); README (the action tools + the corrected scope: read-only actions are
      *proposed*, execution still out); CHANGELOG `[milestone-12]`; ADR 0023 nav + index;
      the ADR 0008 **empty-diff core audit** run and confirmed empty (zero frozen-core
      delta); STATUS; tag `milestone-12`; memory; next-milestone kickoff handed back.

## Scope

**In — the unit breakdown (one PR each, spec each):**

| Unit | Spec | Content |
|---|---|---|
| 1 | 0087 | this plan + the three recorded scope decisions (asked 2026-06-29) |
| 2 | 0088 | router-ambiguity alignment (bare ambiguous term refuses as ambiguous, matching compose); remove the `business/05` pin; prove no battery regression; **adversarial review** |
| 3 | 0089 | `src/tessera/agent/actions.py` grounded-action layer (`ActionProposal` + `incident`/`pr_summary` drafters, field-grounded + verifier-checked, refusals carried, JSON-serializable); leak-guard extended; **ADR 0023**; **adversarial review** |
| 4 | 0090 | `tessera-mcp` `list_actions`/`draft_action` tools (thin transport); no-`mcp`-in-base pin holds; wiring contract test; committed real client-session transcript |
| 5 | 0091 | trust across the action boundary: drafted actions field-grounded + lossless; refusal-carried pin; pinned CI measurement; ADR 0005/0006 re-examined and recorded unforced |
| 6 | 0092 | close: WRITEUP/README/CHANGELOG/STATUS, ADR nav/index, empty-diff core audit, tag `milestone-12`, memory, kickoff |

**Out (explicitly):**

- **Effectful execution and dry-run payload previews.** The maintainer scoped M12 to
  propose-and-approve only. No tool writes, calls an external system, or renders an
  executable payload. Recorded as future work in ADR 0023.
- **An LLM anywhere on the trust path.** Drafting is deterministic selection/templating
  over verifier-passing claims (ADR 0006 holds). No LLM narration is added (ADR 0013
  remains available but unused here). ADR 0005/0006 triggers re-examined at the action
  boundary and recorded not forced.
- **A `business` action kind.** The maintainer's examples are DevEx-shaped (incident, PR
  summary), which map to existing RCA/summary engine outputs. A business-domain action
  (e.g. "draft a renewal notice") is named future work — the catalog is deliberately
  small and grounded in existing answer paths, not invented.
- **Embeddings / the M6–M7 cloud regime.** Untouched. No cloud, no online run, no spend.
- **A new gated eval metric.** Faithfulness stays the single hard CI floor at 1.0; the
  action field-grounding measurement is a pinned test, not a new gate (the M11 pattern).
- **Statefulness / multi-turn agent context.** Each `draft_action` call is answered from
  evidence alone (the stateless property the WRITEUP records); follow-up context remains
  future work.
- **A new frozen-core change.** M12 expects a zero-line frozen-core delta; if a change
  there proves necessary it gets its own ADR and a pre-merge review (none is anticipated).

## Eval impact

- **Faithfulness — held at 1.0, now *also across the action boundary*.** As in M11, the
  headline is a property preserved under a new projection: every field of a drafted action
  is backed by a verifier-passing claim and adds nothing. Measured (Unit 5), not assumed —
  a drafter that fabricated or over-claimed a field would fail the field-grounding pin.
- **Coverage / quality — unchanged.** The action layer is a consumer of existing
  groundings, not a new answer path; the batteries' numbers must not move. Unit 2 (router
  alignment) is vertical-side and must move **no** battery number (the `business/05` gold
  case is scored via `compose`, unaffected; the change touches the router path only).
- **No new gated metric.** Field-grounding stays *pinned*, not gated; faithfulness remains
  the single invariant floor.

## Risks / open questions

- **"Field-grounded" must not become decorative.** The drafter could pass a verdict it
  computed leniently. Mitigated by deriving field-grounding from the *same* `is_supported`
  verdicts the eval gates on (no second verifier) plus an explicit "added-nothing"
  containment check, and by an adversarial test that injects an unsupported field token and
  asserts the verdict drops — the provably-failable proof (ADR 0005 discipline).
- **Router alignment is a precision/recall risk.** Refusing a bare ambiguous term could
  over-refuse a legitimate single-word lookup. Mitigated by defining ambiguity *exactly* as
  `compose`'s own tie condition (so the router and `compose` agree by construction), a
  targeted test that a non-ambiguous single term still grounds, a proof that no battery
  number moves, and a pre-merge adversarial review.
- **The MCP SDK dependency.** Unchanged from M11: opt-in `agent` extra, lazily imported,
  default import graph pinned free of it; the action *substance* carries no MCP dependency
  and is fully CI-tested; the SDK only transports it.
- **The honest edge of propose-and-approve.** Tessera guarantees the *proposal* is
  grounded; it does not and will not execute it — the agent still decides and acts outside
  Tessera. Named in ADR 0023 and the WRITEUP, with execution recorded as future work.
- **Adversarial reviews on non-frozen-core changes.** The maintainer mandated a review on
  *frozen-core* changes; M12 has none. But the action layer (a new trust-bearing surface)
  and the router fix (a precision/recall risk on a shared surface) are the substantive
  risks, so each carries a pre-merge adversarial multi-agent review — honoring the spirit
  of the mandate where the real risk lives.
