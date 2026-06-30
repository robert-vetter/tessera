# 0024. The executable-payload boundary: a dry-run preview, render ≠ send

- **Status:** accepted
- **Date:** 2026-06-30

## Context

ADR 0023 (Milestone 12) extended the trust contract from answers to **action drafts**:
`draft_action` returns an `ActionProposal` whose every `ActionField` carries a recomputed
verifier verdict, faithfulness measured 1.0 across the action boundary. It stopped, by the
maintainer's scope, at *propose-and-approve* — the proposal "renders **no executable
payload**." ADR 0023 named the two future scopes precisely and **declined both** for M12:
**real execution** ("effectful, credentialed, and potentially irreversible — outside the
honest scope of a trust layer") and **a dry-run executable-payload preview** ("a step
toward execution and adds a transport surface the trust story does not need yet").

Milestone 13 revisits the *smaller* of the two. The maintainer's M13 scope (asked &
answered 2026-06-30): the thrust is **the dry-run executable-payload preview**; the target
is **GitHub** (a single real system); the posture is **deterministic / offline /
CI-reproducible / no spend** (the M8–M12 posture). The question this ADR settles: *what*
is a rendered payload, *how* does the trust contract extend from an action draft to the
executable payload, and where is the honest edge now.

The reversal of ADR 0023's "declined dry-run" is deliberate and recorded here: M12
declined it as a transport surface the story did not need *yet*; M13 takes it because it is
the next honest increment of the *same* thesis (read boundary → action-draft boundary →
executable-payload boundary), and because a payload **render** is not a transport — nothing
is sent. The "adds a transport surface" concern is answered by the decision itself: this
layer builds no transport.

## Decision

**A rendered payload is a grounded artifact, built strictly from a verifier-checked
`ActionProposal` (ADR 0023).** A small layer (`tessera/agent/payloads.py`) consumes the M12
proposal and maps it into a `RenderedPayload` — the **exact GitHub wire request** (method,
path, and JSON body) an approver would send. The renderer is a strict *consumer*: it never
reads raw text, never grounds or drafts a second way, never invents content. A declared,
one-system GitHub catalog maps each action kind to an endpoint: `incident` →
`POST /repos/{owner}/{repo}/issues`; `pr_summary` → `POST /repos/{owner}/{repo}/issues/{pr}/comments`.

**Every content value traces to a verifier-passing field; the rest is declared
scaffolding.** The issue `title` is the proposal's verified `title` field; each body
section is one verified `ActionField` placed under a fixed Markdown label; the `{pr}` path
segment is the verified subject field's own cited **pull-request** record id (the first
`PR:`-prefixed support record, required to be a clean single path segment, or the payload
is withheld). Each `PayloadSlot` carries the value, its `verified` verdict, and inline
provenance. Everything else on the wire is fixed *scaffolding*, never asserted grounded:
the section headings (`SECTION_LABELS`) and code fences, the separator, the fixed issue
`labels`, and the unbound `{owner}`/`{repo}` placeholders. A body field whose role has no
declared label is withheld rather than given an invented heading, so the scaffolding
vocabulary is closed. The whole request is a **pure, deterministic template** over the
verified field values plus that scaffolding, so it is *byte-reconstructable* from the
proposal's verified fields alone — a renderer that smuggled an ungrounded token anywhere
(the body, the labels, or the path) fails an independent reconstruction, the
**provably-failable** "added-nothing" check. The renderer introduces **no second
verifier**: payload grounding *reduces to* the M12 field verdicts (already gated at
faithfulness 1.0) plus the added-nothing check.

**Rendered iff `all_grounded`; otherwise withheld.** A refused, route-incompatible,
wrong-domain, or partially-verified proposal — or an `incident` with no grounded title
(GitHub issues require one) — yields a `RenderedPayload` with `rendered=False` carrying the
reason and **no request**. An executable payload is never rendered over ungrounded ground —
the payload-level analogue of ADR 0022's "a refusal never becomes an answer" and ADR 0023's
"a refusal is carried, never drafted over."

**Render ≠ send; nothing executed.** The result declares `sent=False` /
`requires_approval=True`. Tessera builds no transport, opens no socket, holds no credential.
`{owner}`/`{repo}` stay **unbound literal placeholders** — a deployment binding, not
evidence, never asserted grounded. A human or agent binds the target and sends, *outside*
Tessera. This is the honest edge of M13, the strongest claim a trust layer can make about
action: *here is byte-exactly what would leave the system, and all of its content is
grounded* — without itself leaving the system.

**Posture and packaging are unchanged from ADR 0022/0023.** The payload layer is additive
(not ADR 0008 frozen core), pure-stdlib, and deterministic; the leak-guard is extended so
rendering pulls no embedding / LLM / cloud / MCP import toward the verifier. The MCP server
gains one thin tool (`preview_payload`, Unit 3) that only serializes this layer; the SDK
stays the opt-in `agent` extra and the default import graph stays free of `mcp`.

## Consequences

- **The trust substrate now covers the wire payload, not just the draft** — and the
  coverage is *measured*: over cases derived from the data (every failed run, every PR),
  every value of every rendered payload is field-grounded, the body adds nothing, and the
  projection is lossless (spec 0096, a pinned CI property; the M11/M12 boundary pattern).
  Faithfulness stays the single hard gate at 1.0.
- **No write surface and no transport.** Render-only means Tessera guarantees the *request*
  is grounded; it does not, and in M13 will not, send it. The agent still binds the target,
  approves, and acts — the honest edge, named here and in the WRITEUP.
- **No prose synthesis.** Because no LLM is on the payload path, the body carries grounded
  facts (verbatim field values) under fixed labels, not generated narrative. The approver or
  agent may compose prose around the guaranteed facts.
- **The structural-verifier limit (ADR 0005) carries through unchanged:** a slot
  `verified=True` means its value is mechanically supported by its citation, not that
  sending the request is wise. The approver still judges.
- **Honest synthetic-data note:** real GitHub PR comments address the numeric PR *number*;
  the synthetic DevEx ids are `PR-NNN`, used verbatim as the grounded resource id in the
  dry-run path. The shape and grounding of the request are real; the resource id reflects
  our data.

## Alternatives considered

- **Real execution behind approval (effectful).** Declined again, as in ADR 0023: effectful,
  credentialed, potentially irreversible — outside the honest scope of a trust layer. It is
  the named larger next step and, done honestly in a clone-and-run / CI project, would
  *consume* this renderer (a simulated default actuator + an opt-in real path + an execution
  receipt). Recorded as future work, with the posture decision left to the maintainer.
- **A second target system (Jira) or a multi-target abstraction.** Declined for M13 (the
  maintainer chose a single system): one real target keeps the surface small and the trust
  proof sharp. A `PayloadRenderer`-style interface and a Jira renderer are future work — the
  field-grounding contract would carry over unchanged.
- **An LLM-narrated cover summary over the payload (ADR 0013 narration).** Declined: a
  narrated body would be on-top fluency over the grounded request, crossing the determinism
  line and adding spend for a capability the deterministic template covers honestly. The
  ADR 0005/0006 triggers are re-examined at the payload boundary (spec 0096) and recorded
  **not forced**.
- **Assembling the body as free text.** Rejected: any token not traceable to a verified
  field would fail the byte-reconstruction check. The honest choice is verbatim field values
  under declared labels, or no payload at all — not invented prose.
- **Binding `{owner}`/`{repo}` from config and asserting them grounded.** Rejected: the
  target is a deployment choice, not evidence; binding it would assert as grounded something
  Tessera cannot trace. The placeholders stay unbound and are declared scaffolding.
