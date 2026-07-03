# 0129. S2 — knowledge-graph persistence for SAP HANA Cloud's KG engine

- **Phase / milestone:** SAP track S2 (spec 0127 decision 2–3; ROADMAP2:
  "persist the graph to HANA Cloud's GA KG engine (RDF/SPARQL) — 'runs
  on SAP Knowledge Graph'"). Autonomous; carries **ADR 0030**.
- **Issue:** —
- **Status:** approved (autonomous mode).

## Problem

Tessera's knowledge graph is in-process and deterministic — correct for
the trust path, invisible to SAP-native tooling. HANA Cloud's knowledge
graph engine (GA QRC1 2025, RDF/SPARQL via `SPARQL_EXECUTE`) is the
platform's chosen graph substrate; persisting Tessera's graph there
makes the ER/provenance layer inspectable with SAP's own tools and turns
"designed for SAP Knowledge Graph" into a runnable claim. Measured
today: the instance is alive; the triple store awaits the maintainer's
one configuration toggle (spec 0127 decision 2), so this unit ships the
seam and stages the measurement.

**Recorded decisions:**

1. **Mirror, never source of truth** (spec 0127 decision 3, ADR 0030):
   export-only; no answer path reads HANA; frozen core untouched; new
   files only under `tessera/platform/` + `scripts/` + docs.
2. **Structure as triples, provenance as exact literals.** Node kinds,
   names, and structural edges become queryable triples (that is what
   SPARQL should traverse: clusters, mentions, lineage); evidence text,
   locators, and attribute bags become **exact literals** (locator +
   attributes as canonical JSON strings) — byte-fidelity of provenance
   beats queryability of its internals. Floats (scores/confidences)
   serialize as **untyped** `repr()` literals: typed `xsd:double`
   literals invite store-side canonicalization that would break
   round-trip fidelity.
3. **Reversibility survives the mapping.** Resolutions and mentions —
   the additive, withdrawable layers — are reified as their own
   subjects (`urn:tessera:resolution:<i>`, `urn:tessera:mention:<i>`)
   carrying node references, score/confidence, and the human-readable
   reason. Nothing is collapsed; the mirrored graph shows the same
   assertion trail the engine can withdraw.
4. **Losslessness is the contract, tested in-repo.** `graph_to_triples`
   → N-Triples serializer → subset parser → `graph_from_triples` must
   reproduce every real graph (business, devex, github_actions)
   **tuple-exactly** (nodes in insertion order, edges/resolutions/
   mentions in list order). The serializer **raises on duplicate
   identical edges** rather than letting RDF's set semantics silently
   drop one (honest failure over silent loss). Escaping follows
   N-Triples rules (`\" \\ \n \r \t` + control chars) — evidence text is
   adversarial input to a serializer, so injection safety (a text like
   `"} DROP GRAPH <x>` stays inside its literal) is an explicit test
   and a review focus.
5. **Named graph per corpus, idempotent mirror.** Each corpus exports to
   `urn:tessera:graph:<name>` via `DROP SILENT GRAPH` + batched
   `INSERT DATA` (one deterministic batch size), all through
   `SYS.SPARQL_EXECUTE(<sparql>, <headers>, ?, ?)` — the signature
   verified against SAP's tutorial and empirically against the live
   instance (spec 0127).
6. **CI stays key-free; hdbcli stays opt-in.** The HANA adapter imports
   `hdbcli` lazily (the `cloud` extra); a test pins the default import
   graph clean (the `test_vectors` precedent). The adapter is
   contract-tested against a **fake connection** (M6's fake-transport
   pattern): DROP-then-INSERT ordering, batching, header passing
   (`Accept: application/sparql-results+json` on queries), and
   SPARQL-results-JSON parsing.
7. **The one-shot is staged, not run.** `scripts/persist_knowledge_graph.py`
   exports all three graphs and runs three meaningful recorded queries
   (per-graph triple counts; business resolved pairs with confidence +
   reason; mentions of a resolved entity). It runs the day the
   maintainer flips the Triple Store toggle (runbook in DEPLOYMENT.md,
   incl. the possible instance restart and a least-privilege note —
   today's `.env` user is DBADMIN). Until then the honest claim is
   "built and contract-tested against the documented interface; the
   procedure answers on the live instance; the store itself pends one
   toggle."
8. **Adversarial review before merge** (trust-adjacent: a serializer
   over evidence text + a new cloud surface): one focused review;
   findings fixed or recorded.

## Acceptance criteria

- [ ] `tessera/platform/kg.py`: triple mapping, N-Triples serializer +
      subset parser, graph rebuild, SPARQL builders, `HanaTripleStore`,
      `mirror_graph()` orchestration.
- [ ] Round-trip tuple-exact on all three real graphs; escaping,
      injection, duplicate-edge, determinism, fake-transport contract,
      and import-guard tests green.
- [ ] `scripts/persist_knowledge_graph.py` staged; DEPLOYMENT.md gains
      the KG runbook section; ADR 0030 recorded.
- [ ] Gate green; eval byte-identical; frozen core untouched; CI
      key-free.

## Scope

**In:** the module, tests, script, runbook section, ADR.
**Out:** enabling the triple store (maintainer's toggle); reading from
HANA anywhere in the answer path; SPARQL over BYO/connect workspaces
(committed corpora only for the staged one-shot); rdflib or any new
dependency; ontology design beyond the minimal `urn:tessera:`
vocabulary.

## Eval impact

None — platform-layer addition; all six lines byte-identical.

## Risks / open questions

- The engine is young; if the enabled store rejects some construct
  (e.g. `DROP SILENT`), the one-shot records reality and the adapter
  adjusts openly.
- Very large literals (log chunks) ride in `INSERT DATA` batches; the
  batch size is a named constant to tune against the live instance.
