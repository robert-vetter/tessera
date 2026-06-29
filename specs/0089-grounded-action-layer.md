# 0089. The grounded-action layer: propose-and-approve actions built from a grounding

- **Phase / milestone:** Milestone 12, Unit 3 (plan: spec 0087)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

Milestone 11 made Tessera a read-only evidence oracle over MCP and measured the trust
contract across the boundary; it deferred **action proposals** as the named next step
(ADR 0022). The project's thesis is "a trust layer for enterprise AI agents," and an agent
that must *act* — file the incident an RCA describes, draft the summary of a PR — currently
composes that action itself, ungrounded, outside Tessera's guarantee. This unit extends the
same trust substrate to the **action draft**: a structured proposal whose every field
traces to verifier-passing evidence, or it is not proposed at all. Propose-and-approve only;
nothing executed (the maintainer's M12 scope, spec 0087).

## The design (recorded in full in ADR 0023)

`src/tessera/agent/actions.py` (new; additive, not ADR 0008 frozen core; pure-stdlib,
deterministic). An `ActionProposal` is built **strictly from `ground(domain, question)`**
(the M11 boundary):

- **`ActionField`** = `name` (role), `value` (grounded), `verified` (bool), `support`
  (inline provenance). The value is a grounded claim's verbatim text, or a verbatim
  *fragment* of that claim's evidence (a title from an error-signature line / the PR's
  quoted title). `_field` recomputes `verified`: the source claim must have passed the
  boundary verifier **and** the value must be faithful (identical, or normalized-containment
  fragment) — provably failable (a fabricated token → `verified=False`).
- **`ActionProposal`** = `kind`, `domain`, `question`, route, `grounded`/`refused`/`refusal`,
  `fields`, and the propose-and-approve contract `requires_approval=True` / `executed=False`.
  `all_grounded` ⇔ grounded with fields and every field verified.
- **Catalog (small, declared):** `incident` (from `route_kind=="rca"`, domains devex +
  github_actions) and `pr_summary` (from `route_kind=="summary"`, domain devex). Role
  classification reads the engine's own stable claim grammar markers ("Recurring failure:",
  "Documented incident:", "Resolved by:", "Motivating ticket:", a "Ticket "/"PR "/diff
  prefix), so it is not fragile internal coupling.
- **`draft_action(kind, domain, question)`** grounds, then: carries the grounding's refusal
  if it refused; refuses with a precise reason if the route is incompatible or the domain
  does not apply; else maps the grounded claims into role-labeled, field-verified fields.
  Unknown action kind raises `ValueError` (a programming error, like an unknown domain).

## Acceptance criteria

- [ ] `incident` and `pr_summary` draft fully-grounded proposals from devex RCA / change
      groundings; `incident` also drafts from the real `github_actions` connector; every
      field `verified`, `all_grounded` true, `requires_approval`/`executed` set.
- [ ] **Provably-failable field check:** a unit test injects a field whose value adds a
      token its evidence does not support and asserts `verified=False` (the ADR 0005
      discipline, at the action level).
- [ ] A refused grounding (passed/unknown run, out-of-scope), an incompatible route (PR
      question → incident), and a wrong domain each yield a **carried refusal with no
      fields** — never a fabricated action.
- [ ] The proposal is JSON-serializable and round-trips; it is **deterministic across
      `PYTHONHASHSEED`** (subprocess test).
- [ ] **Leak-guard extended:** importing and *calling* `draft_action` pulls no embedding /
      LLM / cloud / MCP module (the verifier stays embedding-free).
- [ ] Faithfulness stays 1.0 on every battery; no battery number moves (the layer is a
      consumer, not a new answer path). Gate green.
- [ ] **ADR 0023** records the grounded-action boundary and the rejected scopes.
- [ ] **Pre-merge adversarial multi-agent review** (the new trust-bearing surface):
      findings triaged; any real defect fixed and pinned before merge.

## Scope

**In:** `tessera/agent/actions.py` (the dataclasses, the catalog, `draft_action`,
`available_actions`); export from `tessera/agent/__init__.py`; `tests/test_actions.py`; the
leak-guard extension in `tests/test_agent.py`; ADR 0023.

**Out:** the MCP `list_actions`/`draft_action` tools + the committed client session
(Unit 4); the boundary measurement over gold cases (Unit 5); any effectful execution or
dry-run payload preview; LLM narration/drafting; a `business`-domain action; any engine or
frozen-core change (`rca.py`/`summaries.py`/`grounded.py` are consumed unchanged).

## Eval impact

**None to the gated numbers** — the action layer consumes existing groundings; faithfulness
stays 1.0 and no battery number moves. The *new* measured property (every action field is
grounded and the projection lossless) is a pinned CI test, landed in Unit 5; this unit pins
the per-field verifier and its provably-failable proof.

## Risks / open questions

- **"Field-grounded" becoming decorative.** Mitigated by reusing the same `is_supported`
  verdicts (no second verifier) plus the added-nothing containment check, and the
  provably-failable test. Recorded in ADR 0023.
- **Role classification coupling to claim text.** It reads the engine's *public* claim
  grammar markers (the same the verifier keys on), and any unmatched claim falls to a
  generic `log`/evidence role, so nothing is dropped or mislabeled into a false role.
- **Generic-trailer titles.** When a log has no specific error-marked line (e.g. a
  ruff-format failure whose only `##[error]` is the exit-code trailer), the title falls back
  to that grounded trailer; the specific cause is still carried in the `log` field. Honest
  degradation, not a fabrication — the title is always a verbatim, verified fragment.
- **The honest edge.** Tessera guarantees the *proposal* is grounded; it does not execute.
  Named in ADR 0023 and (Unit 6) the WRITEUP.
