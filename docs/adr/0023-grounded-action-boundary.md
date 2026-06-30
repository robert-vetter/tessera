# 0023. The grounded-action boundary: propose-and-approve, field-verified actions

- **Status:** accepted
- **Date:** 2026-06-29

## Context

ADR 0022 (Milestone 11) exposed Tessera over MCP as a **read-only** evidence oracle and
*measured* that the trust contract survives the protocol boundary. It explicitly deferred
two scopes as future work: effectful tools, and **action *proposals*** — "a natural next
step … proposals would themselves be grounded, cited, and verifier-checked the same way."

Milestone 12 takes that step (spec 0087), with three maintainer-set, project-shaping
decisions (asked & answered 2026-06-29): the thrust is **grounded actions over MCP**; the
posture is **deterministic / offline / CI-reproducible / no spend** (the M8–M11 posture);
the action scope is **propose-and-approve only — nothing executed**. The question this ADR
settles: *what* is a grounded action, *how* does the trust contract extend from an answer
to an action draft, and where is the honest edge.

## Decision

**An action proposal is a grounded artifact, built strictly from a verifier-checked
`GroundedResult` (ADR 0022).** A small, declared catalog of action kinds — `incident`
(from a failed run's RCA) and `pr_summary` (from a change analysis) — maps a grounding
into a structured, JSON-serializable `ActionProposal` of role-labeled `ActionField`s. The
drafter is a strict *consumer* of the M11 boundary: it never reads raw text, never grounds
a second way, and never synthesizes prose (no LLM on the trust path, ADR 0006).

**Every field traces to a verifier-passing claim, re-checked here.** Each field's value is
either a grounded claim's verbatim text or a verbatim *fragment* of that claim's own cited
evidence (e.g. a title lifted from an error-signature line). `verified` is recomputed at
the action boundary: the source claim must have passed `is_supported` (ADR 0005) **and**
the field value must be faithful to it (identical, or a normalized-containment fragment of
its evidence). A field that introduced a single unsupported token reads `verified=False`,
so the check is **provably failable** — `all_grounded` is earned, not tautological. Field
grounding therefore *reduces to* claim faithfulness (already gated at 1.0) plus an
"added-nothing" check; it introduces **no second verifier**.

**A refusal — or an incompatible grounding — is carried, never drafted over.** If the
grounding refused (a run that *passed*, an unknown run, an out-of-scope question), or
routed to a path the action kind cannot use (asking for an `incident` from a PR question),
or the action does not apply to the domain, the proposal carries the refusal with **no
fields** — the action-level analogue of ADR 0022's "a refusal never becomes an answer." An
action is never proposed on ungrounded ground.

**Propose-and-approve only — nothing executed.** The proposal declares
`requires_approval=True` and `executed=False` in its payload. Tessera performs no side
effect, calls no external system, and renders **no executable payload** (a dry-run payload
preview was offered and declined). A human or agent approves and acts *outside* Tessera.

**Posture and packaging are unchanged from ADR 0022.** The action layer
(`tessera/agent/actions.py`) is additive (not ADR 0008 frozen core), pure-stdlib, and
deterministic; the leak-guard is extended so drafting pulls no embedding / LLM / cloud /
MCP import toward the verifier. The MCP server gains two thin tools (`list_actions`,
`draft_action`, Unit 4) that only serialize this layer; the SDK stays the opt-in `agent`
extra and the default import graph stays free of `mcp`.

## Consequences

- **The trust substrate now covers actions, not just answers** — and the coverage is
  *measured*: every field of every drafted action over the representative cases is
  field-grounded and the projection is lossless (spec 0091, a pinned CI property; the M11
  boundary-equivalence pattern). Faithfulness stays the single hard gate at 1.0.
- **No new write surface or safety posture.** Propose-and-approve means Tessera guarantees
  the *draft* is grounded; it does not and will not execute it. The agent still decides and
  acts outside Tessera — the honest edge, named here and in the WRITEUP.
- **No prose synthesis.** Because no LLM is on the trust path, fields carry grounded facts
  (verbatim claims and evidence fragments), not generated narrative. An action title is a
  lifted error-signature or the PR's own quoted title — never an invented sentence. The
  agent composes prose around the guaranteed facts.
- **The structural-verifier limit (ADR 0005) carries through unchanged:** a field
  `verified=True` means it is mechanically supported by its citation, not that the action
  is wise to take. The approver still judges.

## Alternatives considered

- **LLM-drafted action text (acts on ADR 0005/0006).** Offered and declined for M12: it
  crosses the determinism line and adds spend for a capability the deterministic drafter
  covers honestly. The triggers stay live and are re-examined at the action boundary
  (spec 0091) and recorded not forced.
- **LLM-narrated drafts (ADR 0013 narration boundary).** Offered and declined: a narrated
  cover summary would be on-top fluency over the grounded proposal, but M12 adds no
  narration to keep the unit fully CI-reproducible with no provider. Available for a future
  unit; the proposal's facts would remain the canonical, verifier-checked artifact.
- **Real execution behind approval (effectful).** Declined: effectful, credentialed, and
  potentially irreversible — outside the honest scope of a trust layer. Recorded as future
  work.
- **A dry-run executable-payload preview.** Declined for M12 (the maintainer chose
  propose-only): rendering the exact external API payload is a step toward execution and
  adds a transport surface the trust story does not need yet. Future work.
- **Free-text titles / synthesized summaries.** Rejected: any token not in the cited
  evidence would fail the field verifier; the honest choice is a lifted verbatim fragment
  or no field at all, not invented prose.
- **A `business`-domain action.** Out of scope for M12: the catalog is grounded in existing
  RCA/summary answer paths (the maintainer's examples); a business action is future work,
  not an invented capability.
