# 0053. Vector-store seam — portable in-memory backend + SAP HANA Cloud

- **Phase / milestone:** Milestone 6 — Embeddings on SAP (Unit 3 of 8; plan 0051)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

Unit 2 added the seam that turns text into a vector (GenAI Hub). Those vectors
must be *stored* and *nearest-neighbour searched* to be useful for retrieval.
ADR 0015 puts that storage in SAP HANA Cloud's core vector engine (`REAL_VECTOR`
+ `COSINE_SIMILARITY`). This unit builds the `VectorStore` seam and two backends:
a portable, pure-stdlib in-memory store (deterministic; what tests and any
offline semantic experiment use) and the HANA Cloud backend (the production
target, contract-tested against a fake connection). No retrieval wiring yet
(U4); no live connection (U7).

## Acceptance criteria

- [ ] A `VectorStore` `Protocol` in `tessera/platform/vectors.py`:
      `upsert(items: Sequence[tuple[str, Sequence[float]]]) -> None` and
      `query(vector, k) -> list[VectorMatch]` (`VectorMatch = {id, score}`).
- [ ] `InMemoryVectorStore`: pure-stdlib cosine KNN, **deterministic** (ties
      break by id ascending); handles empty store and `k` larger than the
      population. Fully unit-tested.
- [ ] `HanaVectorStore`: SAP HANA Cloud backend issuing `CREATE TABLE … REAL_VECTOR(dim)`
      (guarded by a `SYS.TABLES` existence check), `UPSERT … VALUES (?, TO_REAL_VECTOR(?)) WITH PRIMARY KEY`,
      and `SELECT … COSINE_SIMILARITY(VEC, TO_REAL_VECTOR(?)) … ORDER BY … DESC LIMIT k`.
      Takes an **injected `connect` callable** so the SQL contract is verified
      against a fake connection — key-free, offline.
- [ ] `hdbcli` (SAP's HANA driver) is an **optional extra** in `pyproject.toml`
      (`uv sync --extra cloud`), imported **lazily** inside the connect helper —
      never at module import. A mypy override silences its missing stubs.
- [ ] A test proves the **default import graph carries no `hdbcli`**: importing
      `tessera.platform.vectors` and the vertical/eval entry modules leaves
      `hdbcli` absent from `sys.modules`. Clone-and-run stays pure-stdlib.
- [ ] Config gains `HANA_*` (`hana_host/port/user/password/database`); `database`
      qualifies the vector table's schema.

## Scope

**In:** `tessera/platform/vectors.py` (protocol + two backends + `_cosine`);
`HANA_*` config; `pyproject` optional `cloud` extra + mypy override;
`tests/test_vectors.py`.

**Out:** wiring embeddings/vectors into retrieval or ER (U4); the eval cases and
precision guard (U5); the provisioning runbook + `.env.example` (U6); the live
HANA connection and the recorded run (U7). The store maps `id → vector` and
returns ids by similarity; it holds **no claim text** — provenance stays with
the records the engine already owns (embeddings serve retrieval only, ADR 0015).

## Eval impact

None — backends exercised only by unit/contract tests. Batteries stay 1.000;
the offline lexical gate is untouched.

## Risks / open questions

- **Exact HANA SQL/connect params are unverified against live SAP** until U7.
  The contract test pins the SQL *shape* we emit; the live smoke test (U7)
  confirms `TO_REAL_VECTOR` string format, `LIMIT` syntax, identifier casing,
  and `hdbcli.dbapi.connect` keywords (`encrypt`, schema). Bare (unquoted)
  identifiers are used so HANA's standard upper-casing applies, matching a
  typical uppercase schema/table.
- **Dimension** is taken from the first upserted vector (`REAL_VECTOR(dim)`);
  all vectors from one embedding model share it. A mismatch would surface at the
  live run, not silently.
- **`hdbcli` is a binary wheel.** Keeping it an opt-in extra + lazy import +
  the import-purity test is what protects the clone-and-run guarantee; the HANA
  backend module must never import it at top level.
