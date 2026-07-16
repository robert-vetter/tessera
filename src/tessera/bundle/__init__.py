"""Trust bundles — portable records a third party re-checks by re-execution.

Act 3 (ROADMAP3, spec 0131): one file per grounded answer or action that
packages the full chain — evidence records → claims → verifier verdicts →
approval → wire request → receipt — so that ``tessera verify`` on another
machine, offline, **re-derives** every claim verdict from the file alone
instead of checking a signature.

The package is a strict *consumer* of the existing seams (the grounded
boundary, the claim-shape grammars, the eval verifier); nothing in the
frozen core changes. Modules arrive unit by unit:

- :mod:`tessera.bundle.serde` — dict round-trips for the whole chain
  (spec 0132): the reconstruction layer everything else stands on.
- :mod:`tessera.bundle.canonical` — the ``tessera-canonical-json-1`` byte
  recipe and digests (spec 0133, ADR 0031).
- :mod:`tessera.bundle.format` — the ``.tsb`` file contract: sections,
  leaf manifest, root, integrity re-check (spec 0133, ADR 0031).
- :mod:`tessera.bundle.emit` — ground a question, package the closure,
  seal the bundle (spec 0133); CLI in :mod:`tessera.bundle.cli`.
- :mod:`tessera.bundle.verify` — offline re-executing verification: both
  layers (integrity + semantics), the verdict taxonomy, named causes
  (spec 0134).
- :mod:`tessera.bundle.ed25519` — pure-Python RFC 8032 signature *verify*,
  so the verify path stays stdlib-only (spec 0135, ADR 0032).
- :mod:`tessera.bundle.signing` — Ed25519 signing + keygen behind the
  optional ``sign`` extra (spec 0135).

Action bundles (spec 0136) reuse the same modules: emission packages a
simulated grounded action's receipt in the ``action`` section, and
verification re-derives that the wire request reconstructs from its slots
and every value traces to a verifier-passing claim.

- :mod:`tessera.bundle.mutations` — the deterministic tamper battery the
  Auditability Floor (``tessera.eval.auditability``, spec 0137) measures
  against, so the verifier's teeth are a CI-pinned number.
- :mod:`tessera.bundle.explain` — a read-only, human-legible rendering of
  a bundle's chain (question → claims → evidence → action), showing
  verify's verdict first (spec 0142).
"""
