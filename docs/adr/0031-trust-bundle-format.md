# 0031. The trust-bundle format: canonical bytes, evidence closure, integrity manifest

- **Status:** accepted (2026-07-10, spec 0133; plan spec 0131)
- **Context:** ROADMAP3 Milestone 20 — portable records a third party
  re-checks offline by re-executing claim-vs-evidence verification.

## Context

A trust bundle is a contract with strangers: once `.tsb` files exist
outside this repository, every byte-level choice — canonicalization,
hashing granularity, what the file must contain for verdicts to be
re-derivable — is expensive to reverse. The scoped novelty claim (spec
0131) also depends on these choices staying honest: the *envelope*
(hashing, signing, transparency logs) is crowded prior art; the claim
rests entirely on the semantic core, so the format's job is to make
re-execution possible and tampering *nameable*, without overclaiming
what the envelope proves.

## Decision

### 1. One JSON document, UTF-8, extension `.tsb`

Top-level sections, format major 1:

| key | content |
|---|---|
| `format` | `{"name": "tessera-trust-bundle", "major": 1, "minor": 0}` |
| `engine` | `tessera_version`, `domain`, `claim_shapes` (dotted identifiers, declared order) |
| `result` | the `GroundedResult` dict, verbatim — its per-claim `verified` flags are the recorded emission verdicts |
| `evidence_closure` | `kind` + the full graph snapshot and knowledge base (`serde` shapes) |
| `integrity` | `canonicalization`, `leaves` (the manifest), `root` |
| `action` | reserved, `null` until unit 0136 |
| `signature` | reserved, `null` until unit 0135 |
| `anchor` | reserved, `null` until unit 0138 |

Reserving the planned keys now means format major 1 survives the whole
act — a verifier for major 1 reads every bundle the act will ever emit.
A future key not in this table is a **minor** bump (old verifiers ignore
it); a change to any existing section's meaning or to the
canonicalization is a **major** bump.

### 2. Canonical bytes: `tessera-canonical-json-1`

`json.dumps(value, sort_keys=True, ensure_ascii=False,
separators=(",", ":"))`, UTF-8-encoded. This is the `_canonical_request`
recipe that already produces the cross-process-stable idempotency key
(ADR 0026), generalized into `bundle/canonical.py` (the execution module
is not modified). The identifier string is recorded inside every bundle
(`integrity.canonicalization`), so the recipe can never drift silently —
a different recipe is a different identifier, visible to every verifier.

**Deliberately not RFC 8785 (JCS)** and never claimed to be: JCS
prescribes ECMAScript number serialization; this chain's data model is
strings + `Decimal` end-to-end (the only floats are ER confidences,
which Python's `repr`-based JSON round-trips exactly — pinned by spec
0132's fidelity tests). Claiming JCS conformance would buy interop we
don't need at the cost of float-formatting machinery we'd have to get
perfectly right on every platform. A smaller, exactly-specified recipe
is the honest choice; the mandatory-caveats rule (spec 0131) bans
"RFC 8785" from all public copy.

### 3. Evidence closure: the full corpus snapshot (v1)

`evidence_closure.kind = "full-graph-snapshot"`: the bundle carries the
**whole** graph (nodes, edges, resolutions, mentions) and the knowledge
base, not just the cited records. Rationale (spec 0131 D4): whole-graph
claim shapes — `superlative_conclusion` and `compare_conclusion`
re-rank/recompute over *every* cluster (spec 0019) — cannot be
re-derived from cited records alone, and a cited-records-only bundle
would let a malicious bundler omit the larger customer and make a false
superlative "verify". Packaging the full closure closes that attack **by
construction**, not by policy. The committed corpora are small (sizes
measured and recorded at the milestone close); cited-only slimming for
large corpora is named future work and would arrive as a new closure
`kind`, never a silent change. A bundle whose closure kind the verifier
does not recognize can only ever degrade (unit 0134's taxonomy), never
upgrade to `RE-DERIVED`.

### 4. Integrity: a leaf manifest and a depth-1 root

`integrity.leaves` maps a leaf name to `sha256:<hex>` of that content's
canonical bytes:

- `node:<record-id>` — one leaf **per graph node**, so integrity
  tampering names the exact record;
- `engine`, `result`, `graph.edges`, `graph.resolutions`,
  `graph.mentions`, `kb`, `action` — one leaf per remaining section.
  `action` is a leaf from day one (hashing its literal `null` until unit
  0136 fills it), so that unit extends content, not the manifest shape.
  `signature` and `anchor` are attestations **over** the sealed root and
  are structurally excluded from the manifest they attest — a signature
  inside its own signed content would be circular.

`integrity.root` is sha256 over the canonical bytes of the manifest
itself (whose keys sort deterministically). This is a **depth-1 Merkle
construction, and the ADR says so plainly**: a deeper tree exists to
serve inclusion proofs for *partial* data, and a v1 bundle always
travels whole — every verifier holds every leaf, so a tree would add
machinery without adding a guarantee. If a future closure kind ships
partial evidence, that format-major bump introduces a real tree; the
root's meaning ("commitment over all leaves") is unchanged by that
upgrade path. External anchoring (unit 0138) anchors the root.

What the integrity layer honestly proves: **that the file is the file**
— which section (down to the record) changed since sealing. What it can
never prove is that the content is *true*; that is the verifier's job
(unit 0134), and conflating the two is exactly the category error the
act exists to name (spec 0131). Verify reports the two layers
separately.

### 5. Engine pins

`engine.tessera_version` (via `importlib.metadata`, fallback `"0.0.0"`)
and `engine.claim_shapes` — the `module.qualname` dotted names of the
domain's declared shape tuple, in declared order (business: six;
devex/github_actions: empty — the generic grammars). Identifiers are a
*proxy*: a function body can change under a stable name, so identifier
equality plus version equality is the only combination read as "same
grammar". Unit 0134 downgrades on any mismatch (`NOT-EVALUABLE`, naming
both sides) rather than re-deriving under a different grammar and
calling it the same verdict.

### 6. Emission builds its own engines

`build_bundle()` replicates `ground()`'s four public steps on a fresh
graph/kb so the packaged snapshot is by construction the same object the
packaged verdicts were computed against. No dependency on the
module-private engine cache; a consistency test pins fresh == cached.

## Consequences

- Unit 0134 can implement verify entirely against this contract: recheck
  leaves → recheck root → reconstruct via `serde` → re-run
  `is_supported` under the pinned shapes → report the semantic and
  integrity layers separately.
- Every future unit (signature, action, anchor) extends the manifest
  instead of restructuring the file; format major 1 holds for the act.
- The canonicalization identifier inside the bundle makes the byte
  recipe self-describing; the 3-OS determinism matrix (unit 0137) guards
  the recipe's cross-platform stability.
- Full-closure bundles are larger than cited-only bundles would be —
  accepted deliberately; the sizes are measured and recorded, and any
  future slimming is a visible format event.
