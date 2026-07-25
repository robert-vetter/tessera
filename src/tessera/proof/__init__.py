"""The bounded soundness theorem (spec 0147, ADR 0037).

Everything else in this project measures: a mutation battery, a
conformance benchmark, an eval with a gated floor. This package *proves* —
within an explicitly stated bound, and with the bound printed next to every
result.

Over a bounded universe of bundle states enumerated **in full**, it
machine-checks that a PASS from the re-executing verifier implies the state
is honest: no false PASS exists, not merely "none was found". Two
deliberately flawed verifiers are checked in the same run and must be
refuted, so the checker is demonstrably able to fail; and the model's claim
semantics are differentially pinned to the shipping verifier.

- :mod:`tessera.proof.model` — the state model and the verifier models.
- :mod:`tessera.proof.universe` — exhaustive enumeration and its size formula.
- :mod:`tessera.proof.bridge` — model vs. real ``is_supported``.
- :mod:`tessera.proof.check` — the theorem runner and the certificate.
"""
