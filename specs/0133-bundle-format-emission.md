# 0133. Bundle format + emission — one sealed file per grounded answer

- **Phase / milestone:** ROADMAP3 Milestone 20, unit 2 (plan: spec 0131).
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0131).

## Problem

Unit 0132 proved the chain reconstructs losslessly from dicts. This unit
defines the **file**: the `.tsb` trust bundle — a single JSON document
carrying the grounded result, the full evidence closure (graph + knowledge
base), the engine/shape pins, and an integrity manifest sealed by a root
hash — and the CLI that emits it: `tessera bundle "<question>" --domain
<d> -o answer.tsb`. The offline re-executing verifier is unit 0134; this
unit's contract is that everything 0134 needs is in the file, sealed, and
byte-stable across machines.

The format decisions are hard to reverse once bundles exist in the wild,
so they carry **ADR 0031**.

## Decisions (details and rationale in ADR 0031)

1. **One JSON document, UTF-8, extension `.tsb`.** Top-level sections:
   `format` (name + major/minor), `engine` (tessera version, domain,
   claim-shape identifiers), `result` (the `GroundedResult` dict,
   verbatim — its per-claim `verified` flags ARE the recorded emission
   verdicts; no duplicate verdict section), `evidence_closure`
   (`kind="full-graph-snapshot"` + the graph and knowledge-base dicts,
   spec 0131 D4), `integrity` (leaf manifest + root +
   canonicalization identifier). The keys `action` (unit 0136),
   `signature` (unit 0135), and `anchor` (unit 0138) are **reserved
   now** — present with value `null` — so format major 1 never has to
   change for the planned units.
2. **Canonical bytes: `tessera-canonical-json-1`.** `json.dumps` with
   `sort_keys=True`, `ensure_ascii=False`, separators `(",", ":")`,
   UTF-8-encoded — the `_canonical_request` recipe (ADR 0026),
   generalized into `bundle/canonical.py` without touching
   `agent/execution.py`. Not RFC 8785 and not claimed to be (spec 0131
   D5); the identifier is recorded in every bundle so a future change is
   a visible format event, never a silent drift.
3. **Integrity: a leaf manifest + a depth-1 root.** One leaf per graph
   node (keyed `node:<record-id>` — tampering names the exact record),
   plus section leaves (`engine`, `result`, `graph.edges`,
   `graph.resolutions`, `graph.mentions`, `kb`, `action`). The root is
   sha256 over the canonical bytes of the sorted manifest. A deeper
   Merkle tree buys nothing while bundles always travel whole (every
   verifier holds every leaf; no inclusion proofs needed) — recorded in
   ADR 0031 with the upgrade path if partial bundles ever exist. The
   `action` section is a leaf **from day one** (hashing its literal
   `null` now), so unit 0136 extends content, not the manifest shape;
   `signature` and `anchor` are attestations **over** the sealed root
   and can never be inside the manifest they attest.
4. **Engine pins (spec 0131 D6).** `engine.tessera_version` via
   `importlib.metadata` (fallback `"0.0.0"`), `engine.domain`, and
   `engine.claim_shapes` = the dotted identifiers
   (`module.qualname`) of the domain's declared shape tuple, in order.
   Identifiers are a *proxy* pin (a body can change under a stable
   name); the honest pin is the version — both are recorded, and unit
   0134 downgrades on mismatch rather than guessing.
5. **Emission builds its own engines.** `build_bundle()` replicates
   `ground()`'s four public steps (`domain()`, `build()`, `route()`,
   `serialize_answer()`) on a **fresh** graph/kb instance so the packaged
   snapshot is by construction the exact object the packaged verdicts
   were computed against — no reach into the module-private engine
   cache. Corpus construction is deterministic (pinned by 0132's
   round-trip tests on freshly built instances), so a fresh build equals
   the cached one; a consistency test pins `build_bundle().result ==
   ground()` anyway.
6. **CLI via the front door.** `cli.py` reserves the `bundle` subcommand
   (the spec-0117 dispatch pattern; `verify` follows with unit 0134) and
   routes to `tessera/bundle/cli.py`. Extends the recorded spec-0117
   residual: a business question literally starting with "bundle" would
   mis-route — same class, same mitigation (rephrase or
   `tessera-chat`).
7. **Refusals are bundleable.** A refusal is a first-class outcome
   (`result.refused=true`, no claims); the bundle carries it with the
   same closure and seals it the same way. What verify re-derives for a
   refusal is unit 0134's contract.

## Scope

**In:** `tessera/bundle/canonical.py`, `tessera/bundle/format.py`,
`tessera/bundle/emit.py`, `tessera/bundle/cli.py`, the one-line `bundle`
dispatch in `tessera/cli.py` (+ help text), ADR 0031,
`tests/test_bundle_format.py`.
**Out:** verify/taxonomy/exit codes (0134), signing (0135), action
sections beyond the reserved key (0136), docs page (0134), Rekor (0138).

## Acceptance criteria

- [ ] `tessera bundle` emits a `.tsb` for a grounded answer and a refusal
      in each of the three committed domains; every emitted bundle's
      root recomputes from its content.
- [ ] Byte-stability: the same (domain, question) emitted under two
      different `PYTHONHASHSEED` values in separate interpreters is
      byte-identical.
- [ ] Tampering any graph node in the dict makes exactly that
      `node:<record-id>` leaf mismatch (named), and the root mismatch.
- [ ] `engine.claim_shapes` records the business shapes in declared
      order; devex/github_actions record `[]`.
- [ ] `build_bundle().result` equals `ground()`'s result for the same
      inputs (fresh-vs-cached engine consistency).
- [ ] Gate green; six eval lines byte-identical; only `tessera/cli.py`
      touched among existing files (dispatch + help).

## Eval impact

None — additive package modules + one dispatch line.

## Risks / notes

- Bundle size: the github_actions corpus is the largest; emitted sizes
  are measured by the tests and recorded in STATUS at the milestone
  close (spec 0131 risk item). If impractical, the honest fallback is a
  documented domain scope, not a silent closure cut.
- `result.claims[].verified` doubles as the recorded verdict store;
  0132 already pinned that a stored-verdict lie cannot survive
  reconstruction of *derived* fields — re-deriving the per-claim flags
  themselves is exactly unit 0134's job.
