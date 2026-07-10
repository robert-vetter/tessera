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
"""
