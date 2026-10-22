"""The issuance ledger (spec 0151, ADR 0041).

Ten layers answer *"is this receipt honest?"*. This one answers the
question an auditor asks second and a regulator asks first: **"is this all
of them?"** — an append-only Merkle log of issued receipts with the two
Certificate-Transparency proofs that make such a log worth keeping,
inclusion and consistency.

- :mod:`tessera.ledger.tree` — the RFC-6962 tree and its proofs.
- :mod:`tessera.ledger.store` — the append-only file and the detached
  inclusion-proof artifact.

The honest limit travels with the guarantee: an operator keeping two logs
can show two heads, and no offline check detects that. Consistency proofs
make *rewriting* detectable to anyone who has seen an earlier head; making
heads unforgeably public is what a transparency log is for (unit 0138,
reserved). See ``docs/LEDGER.md``.
"""
