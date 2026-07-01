# 0101. Trust across the execution boundary (the pinned CI measurement)

- **Phase / milestone:** Milestone 14 — Effectful execution behind approval (Unit 4).
  See the plan (spec 0098) and ADR 0025.
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

Units 2–3 built the execution layer and exposed it over MCP. This unit **measures** the
trust contract across the execution boundary and pins it in CI — the M11/M12/M13 pattern
(`tests/test_boundary.py`, `tests/test_actions_boundary.py`,
`tests/test_payloads_boundary.py`), a fourth time. Over cases **derived from the data**
(every failed run → an incident execution, every PR → a pr_summary execution; the
expectations are data-derived, not hand-authored — anti-tautology, ADR 0007), the
capability's effect on the metric is *known* (principle 3).

## Acceptance criteria

- [ ] `tests/test_execution_boundary.py`, gated in CI (offline, pure-stdlib, no SDK):
  - [ ] **Every simulated execution consumed an `all_grounded` payload and its receipt
        is a lossless record** — the receipt's request equals the M13 rendered payload's
        request (method/path/body); each non-path content slot projects exactly one of
        the grounding's claims (value, support ids, and the verdict recomputed
        *independently from the grounding*, not read from the receipt); the `{pr}`
        resource traces to the PR record; `sent` is false, `simulated` true.
  - [ ] **Faithfulness is 1.0 across the execution boundary** — counted over every slot
        of every derived execution's receipt, every slot is verifier-passing (provably
        failable: a fabricated/over-claimed value fails it).
  - [ ] **Nothing executes over ungrounded ground** — a passed/unknown run (synthetic +
        real), an out-of-scope question, an incompatible route, and a wrong domain each
        yield a withheld receipt with no request and nothing sent.
  - [ ] **The real path is earned** — against an injected fake transport,
        `GithubActuator` sends a POST **iff** approved and credentialed, never otherwise;
        the real network is never touched (the property is measured without the SDK).
  - [ ] **ADR 0005/0006 re-examined at the execution boundary and recorded not forced**
        (a documentation pin).
- [ ] Gate green under multiple `PYTHONHASHSEED` values; **zero frozen-core delta**.

## Scope

**In:** the pinned CI boundary test. It drives the execution layer's simulated actuator
and an injected fake transport; it grounds/renders via the existing M11/M13 layers. The
data-derived cases mean the measurement widens automatically as the corpus grows.

**Out:** a new gated eval metric (faithfulness stays the single hard floor at 1.0; this
is a *pinned* property, as in M11/M12/M13); any real network; any frozen-core change; a
second target.

## Eval impact

- **Faithfulness — held at 1.0, now also across the execution boundary.** The headline
  is a property preserved under a new projection: every receipt slot is backed by a
  verifier-passing field, the receipt's request equals the M13 payload (lossless), and
  nothing executes over ungrounded ground. Measured, not assumed.
- **Coverage / quality — unchanged.** The execution layer is a consumer, not a new
  answer path; no battery number moves.
- **No new gated metric.** The property is *pinned*, not gated.

## Risks / open questions

- **"Lossless" must not become decorative.** Mitigated by recomputing each slot's verdict
  independently from `ground()` (not reading the receipt) and by asserting the receipt's
  request equals the independently-rendered M13 payload — a fabricated or dropped value
  fails.
- **The earned real send.** Pinned by a fake-transport contract inside the boundary
  itself, so "sent iff approved+credentialed" is measured, not assumed — without touching
  the network.
