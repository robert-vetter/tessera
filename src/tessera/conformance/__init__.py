"""The Verification Gap — a conformance benchmark for agent-receipt
verification (spec 0146, ADR 0036).

Tessera's positioning rests on a comparative claim: every shipping agent
receipt verifies *integrity*; none verifies *content*. This package turns
that assertion into a measurement anyone can re-run — faithful,
steelmanned implementations of the verification methods published in 2026,
graded against an attack battery under two explicitly named threat models.

- :mod:`tessera.conformance.methods` — the reference verifiers, each
  documenting the source it models and the scope that source claims.
- :mod:`tessera.conformance.attacks` — the attack battery (five families),
  reusing the CI-pinned mutation generators where they exist.
- :mod:`tessera.conformance.runner` — grades every method × attack ×
  threat model into a scorecard.

The honest result is not "we win": under the outside-tamperer model the
signature-based methods detect everything and re-execution adds no
detection power. The gap opens only under the model that actually applies
to an AI agent's own receipt — where the issuer is the party whose
honesty is in question.
"""
