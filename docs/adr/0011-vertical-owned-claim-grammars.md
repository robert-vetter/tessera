# 0011. Verticals own their claim grammars; the battery carries them to the verifier

- **Status:** accepted
- **Date:** 2026-06-10

## Context

The faithfulness verifier (`eval/metrics.py`, ADR 0005) accumulated its shapes
historically: the generic ones (verbatim containment; the shared-fragment
grammar ADR 0008 sanctioned) sit beside five grammars that only the business
vertical's answer paths ever compose — aggregate recomputation ("net order
value"), customer/address count matching, the renewal-date conflict disclosure
(importing `tessera.business.conflicts` into eval internals), refuse-to-sum,
and the compare/superlative conclusions. ADR 0008 recorded this as a leak and
scheduled the relocation for Phase 4; the namespace move (spec 0037) made it
glaring — the engine's metric module speaking one vertical's language.

The constraint pulling the other way is ADR 0005: the faithfulness metric must
stay **central, transparent, and auditable**. Whatever mechanism moves the
grammars out must not let "faithfulness" quietly mean different things per
vertical.

## Decision

**A claim shape is a value the battery declares.** The contract
(`tessera.eval.metrics.ClaimShape`) is one deterministic function:
`(claim, nodes, graph) -> bool | None` — a `bool` is an owned verdict, `None`
means "not my grammar." `is_supported` consults, in order: the battery's
declared shapes, then the generic shared-fragment grammar, then generic
verbatim containment; anything unclaimed is unsupported. **Scoring semantics
do not change**: faithfulness remains the fraction of claims whose support is
deterministically verified, floor-gated at 1.0 everywhere.

**The grammars move home.** `tessera/business/claims.py` holds the six
business shapes, logic-identical; the business battery declares them. The
devex battery declares **none** — its claims are verbatim snippets plus the
generic shared-fragment grammar, which is itself evidence of the engine's
generality.

**Wiring stays explicit.** Shapes reach the harness only through the
`Battery` value built in `tessera/eval/registry.py` (the ADR 0009 pattern).
No entry points, no discovery, no registration side effects: the complete
verifier behaviour for any battery is readable in two files — `metrics.py`
(the generic core) and the vertical's `claims.py`.

**One deliberate precedence change, stricter not laxer:** a vertical
conclusion grammar now owns its verdict *ahead of* generic containment
(previously the conflict shape ran after it). If a claim speaks a conclusion
grammar, its recomputation governs; being a verbatim substring of some record
can no longer rescue a failed conclusion. No corpus claim hits the difference
— both batteries' numbers reproduced exactly — but the rule is now principled
rather than accidental.

## Consequences

- `eval/metrics.py` contains zero vertical vocabulary; principle 5 holds in
  the eval internals, not just the engine.
- Adding vertical N+1 with new claim shapes = one `claims.py` + one line in
  its battery; the metric machinery is untouched.
- The auditability ADR 0005 demands is preserved by construction: shapes are
  pure deterministic functions, adversarially tested where they live, and the
  declared tuple makes a vertical's entire grammar surface explicit.
- Accepted cost: the tri-state contract is subtler than a plain bool —
  documented on the type, and the failure mode (a shape returning `False`
  too eagerly) is exactly what the adversarial tests pin.

## Alternatives considered

- **Leave the shapes in `metrics.py`.** Rejected: the recorded leak would
  become permanent precisely when the project claims a clean core/vertical
  boundary as a milestone.
- **Plugin/entry-point discovery of shapes.** Rejected (again — ADR 0008):
  dynamic discovery invites silently missing or "creative" per-vertical
  shapes; an explicit tuple keeps the measured grammar visible in one line.
- **Per-vertical verifier subclasses.** Rejected: inheritance hides which
  grammar fired; a flat ordered tuple of pure functions is inspectable and
  has no override surface.
- **A DSL/declarative grammar table.** Rejected: five regex-anchored
  functions do not justify a meta-language; the DSL itself would become the
  un-auditable part.
