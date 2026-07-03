# 0030. Knowledge-graph persistence: a mirror on HANA's KG engine, never a source of truth

- **Status:** accepted
- **Date:** 2026-07-03
- **Spec:** 0129 (SAP track S2; plan spec 0127)

## Context

Tessera's knowledge graph is deliberately in-process and deterministic:
ingestion builds it from committed data, the answer layers traverse it,
and the additive resolution/mention layers keep every merge inspectable
and reversible (ADR 0004). SAP's platform direction makes the **SAP
HANA Cloud knowledge graph engine** (GA QRC1 2025; RDF triples, SPARQL
1.1 via the `SPARQL_EXECUTE` procedure) the natural interop surface —
"runs on SAP Knowledge Graph" is a credibility claim ROADMAP2 names
explicitly. Persisting the graph there must not compromise the two
properties everything else rests on: the deterministic offline trust
path, and byte-exact provenance.

Measured constraint (2026-07-03): the project's HANA Cloud instance is
alive (cloud version 2026.14.7) and `SYS.SPARQL_EXECUTE` exists, but the
triple store is not enabled ("No active TripleStore found in
landscape") — enablement is an account-owner instance toggle. The seam
therefore ships fully tested offline, with the online measurement
staged.

## Decision

1. **The mirror boundary.** HANA persistence is an **export**: the
   in-process graph stays the single source of truth; no answer path,
   verifier, or eval reads from HANA. The mirror may lag, vanish, or be
   rebuilt at will (`DROP SILENT GRAPH` + `INSERT DATA`, one named
   graph per corpus: `urn:tessera:graph:<name>`), which is what makes
   it safe: losing it loses nothing.
2. **Structure as triples, provenance as exact literals.** What SPARQL
   should traverse becomes triples: node kind/name, structural edges
   (`urn:tessera:rel:<relation>`), reified resolutions and mentions
   (own subjects with node references, scores, confidences, reasons —
   the reversible assertion trail, visible to SAP tooling). What must
   survive **byte-exactly** becomes opaque literals: evidence text,
   `Origin.source`/`ingested_at`, and locator + attribute bags as
   canonical JSON strings. Numbers serialize as **untyped** `repr()`
   literals — typed `xsd:double` invites store-side canonicalization
   (`0.85` → `8.5E-1`) that would break round-trip fidelity; we trade
   SPARQL-side numeric ordering on confidences for exactness.
3. **Losslessness is the tested contract.** Serializer → subset
   N-Triples parser → rebuild must reproduce each committed graph
   tuple-exactly (node insertion order, edge/resolution/mention list
   order). Where RDF's set semantics cannot represent a graph feature
   (duplicate identical edges), the serializer **fails loudly** instead
   of losing data silently.
4. **Stdlib only; the driver stays opt-in.** No rdflib: the emitted
   subset of N-Triples (IRIs percent-encoded into `urn:tessera:`,
   escaped literals) is small enough to serialize and parse correctly
   in-repo, and the project's zero-dependency clone-and-run rule
   (Phase 0) outranks a convenience library. `hdbcli` remains the lazy
   `cloud` extra (ADR 0015 precedent), contract-tested against a fake
   connection; CI stays key-free.

## Consequences

- "Runs on SAP Knowledge Graph" becomes one instance toggle + one
  staged script away, without any change to the trust path — the same
  posture that made the `VECTOR_EMBEDDING` closes credible (ADR 0015).
- The ER story becomes demonstrable in SAP's own tools: resolved
  clusters, confidences, and reasons are SPARQL-queryable objects.
- Accepted cost: confidences aren't numerically ordered in SPARQL
  (untyped literals), and the mirrored graph is read-only interop — a
  consumer wanting live graph state must rebuild the mirror.
- Accepted cost: the N-Triples parser handles exactly our emitted
  subset (documented); it is a round-trip fixture, not a general RDF
  reader.

## Alternatives considered

- **rdflib (or another RDF library).** Rejected: a new runtime
  dependency against the stdlib rule, for a serializer we can write,
  test, and audit in a few hundred lines.
- **Relational mirror (nodes/edges tables + HANA Graph workspace).**
  Rejected for S2: the roadmap claim is the *KG engine* (RDF/SPARQL) —
  SAP's own strategic graph surface; a relational mirror proves less
  and still needs the same fidelity work.
- **Typed literals for numerics/dates.** Rejected: store
  canonicalization risks silent drift between what we wrote and what we
  read back; fidelity is the product here.
- **HANA as the primary graph store.** Rejected outright: it would put
  a network dependency inside the trust path and break offline
  determinism (principles 1, 4; ADR 0003's spirit).
- **Skipping the parser (one-way export).** Rejected: without an
  in-repo round-trip, "lossless" would be an assertion, not a tested
  contract — exactly the kind of decorative claim this project refuses.
