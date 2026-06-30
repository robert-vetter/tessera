# 0094. The GitHub payload renderer — dry-run, render ≠ send

- **Phase / milestone:** Milestone 13 (spec 0093), Unit 2.
- **Issue:** —
- **Status:** approved (autonomous mode; the design was recorded in spec 0093 and is
  settled in **ADR 0024** here)

## Problem

Milestone 12 produces a verifier-checked `ActionProposal` whose every field carries a
recomputed verdict — but it "renders no executable payload" (its own docstring). An
agent that must act still composes the wire request itself, ungrounded. This unit
renders that request: the **exact GitHub payload** an approver would send for a
grounded action, with every value traced to a verifier-passing field, and **sends
nothing**. It carries the measured trust contract one boundary further (read → action
draft → executable payload), keeping Tessera a trust layer, not an actuator.

## Acceptance criteria

- [ ] `src/tessera/agent/payloads.py` (additive, not frozen core): `RenderedPayload`
      + `PayloadSlot` (JSON-serializable), `render_payload(proposal)` (pure core), and
      `preview_payload(action, domain, question)` (draft + render).
- [ ] Two declared GitHub targets: `incident` → `POST /repos/{owner}/{repo}/issues`
      (title + body + `labels:["incident"]`); `pr_summary` →
      `POST /repos/{owner}/{repo}/issues/{pr}/comments` (body; `{pr}` derived from the
      verified subject field's cited **pull-request** record id — the first `PR:`-prefixed
      support record, a clean single path segment, or the payload is withheld — and
      traced).
- [ ] **Rendered iff `proposal.all_grounded`** (and, for `incident`, a grounded title
      exists); otherwise a `RenderedPayload` with `rendered=False` carrying the reason
      (the proposal's refusal, or "not fully grounded") and **no request** — the
      payload analogue of "a refusal never becomes an answer."
- [ ] **Every content value is one verified field** (title, each body section, the
      `{pr}` resource id) — copied verbatim, each slot carrying its `verified` verdict
      and inline provenance. Everything else is declared scaffolding (section labels,
      code fences, separators, the fixed issue `labels`, the unbound `{owner}`/`{repo}`);
      a body field with no declared label is withheld, not given an invented heading. No
      second verifier is introduced.
- [ ] **The body adds nothing**: the whole wire request is a pure, deterministic
      template (`## {label}\n{value}`, code-fenced for log/diff, joined by a fixed
      separator; `labels` fixed; `{pr}` the traced resource) over exactly the verified
      field values plus that scaffolding — so it is byte-reconstructable from the
      verified fields alone. A unit test rebuilds the expected request independently and
      asserts equality (provably failable: a smuggled token anywhere — body, labels, or
      path — fails it).
- [ ] **Render ≠ send**: `sent=False`, `requires_approval=True`; `{owner}`/`{repo}`
      stay unbound literal placeholders (a deployment binding, not evidence); no
      transport, socket, or credential.
- [ ] `{owner}`/`{repo}` are declared scaffolding, **never asserted grounded**; only
      content values and the traced `{pr}` resource id are slots.
- [ ] Leak-guard (`tests/test_agent.py`) extended to call `preview_payload` and assert
      no embedding/LLM/`hdbcli`/`mcp` import is pulled.
- [ ] Deterministic across `PYTHONHASHSEED`; JSON round-trips; full stdlib test
      coverage incl. the withheld paths (refusal, wrong domain, incompatible route,
      a synthetic partially-verified proposal, and a no-title incident).
- [ ] **ADR 0024** records the payload boundary (dry-run, render ≠ send, field-traced,
      revisiting ADR 0023's declined dry-run) + rejected scopes (real execution;
      multi-target/Jira; LLM-narrated body).
- [ ] **Mandated pre-merge adversarial multi-agent review** (new trust-bearing
      surface) before merge; confirmed findings fixed and pinned.

## Scope

**In:** the renderer, the two GitHub targets, the trust properties above, ADR 0024,
the leak-guard extension, unit tests.

**Out:** the MCP `preview_payload` tool + committed session (Unit 3); the gated
data-derived boundary measurement (Unit 4); a second target/Jira; any sending,
transport, credential, or execution; an LLM on the path; a `business` payload kind.

## Eval impact

None on the batteries (the renderer is a consumer of existing proposals, not an answer
path). The new property — faithfulness across the payload boundary — is *measured* as a
pinned test in Unit 4; this unit's tests prove the renderer's field-grounding,
byte-reconstruction, and withheld behaviour. Faithfulness stays the single gate at 1.0.

## Risks / open questions

- **The body could smuggle ungrounded text.** Mitigated by the byte-reconstruction /
  strip check and the mandated adversarial review (the M12 review caught exactly this
  seam class).
- **`{pr}` is content, not scaffolding** — it identifies the target resource, so it is
  derived from a grounded field and traced (a test pins it). `{owner}`/`{repo}` are
  scaffolding and stay unbound. Honest note: real GitHub PR comments use the numeric PR
  number; our synthetic ids are `PR-NNN`, used verbatim as the grounded resource id in
  the dry-run path (recorded in ADR 0024 / the docstring).
- **No-title incident.** GitHub issues require a title; a (theoretical, absent from the
  data) incident with no grounded title is **withheld**, not given a fabricated title.
