# 0132. Bundle serialization round-trip — the reconstruction layer

- **Phase / milestone:** ROADMAP3 Milestone 20, unit 1 (plan: spec 0131).
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0131).

## Problem

A trust bundle is only as good as its reconstruction: `tessera verify`
(unit 0134) must rebuild, **from a JSON file alone**, exactly the objects
the live verifier consumes — `Claim`s with their `EvidenceRecord`
support, the full `KnowledgeGraph` (nodes, edges, resolutions, mentions),
and the boundary/action-chain objects whose recorded verdicts it
re-derives. Today the repository has `to_dict` on every boundary object
(`GroundedResult`, `RenderedPayload`, `ActionProposal`,
`ExecutionReceipt` and their parts) but **no `from_dict` anywhere**, and
the core objects (`EvidenceRecord`, `Claim`, `Node`, the graph) have no
dict form at all.

This unit builds that layer and nothing else: no bundle format, no
hashing, no CLI — those are units 0133/0134. Keeping serde separate means
its fidelity is testable in isolation, before any envelope exists.

## Decisions

1. **One new module, `tessera/bundle/serde.py`** (package
   `tessera/bundle/`, spec 0131 D1) — a strict *consumer* of the existing
   seams. No file under the frozen core or the agent layer changes; serde
   consumes their public `to_dict` output and constructors.
2. **Dict shapes.** Boundary objects: serde's `from_dict` functions are
   exact inverses of the **existing** `to_dict` output (derived fields
   like `all_verified`, `all_grounded`, and `locator.render` are
   recomputed by the objects themselves, not stored state — `from_dict`
   ignores them). Core objects (locator/origin/record/claim, node/edge/
   resolution/mention, graph, knowledge base): serde defines both
   directions; shapes mirror the constructor fields one-to-one.
3. **Order is preserved, not sorted.** `graph_to_dict` serializes nodes,
   edges, resolutions, and mentions in the graph's own insertion order,
   and `graph_from_dict` replays them through the ordinary `add_*`
   methods — so a rebuilt graph is **tuple-exact** (`nodes`, `edges`,
   `resolutions`, `mentions` all equal as tuples), the same losslessness
   standard `platform/kg.py` set (its round-trip test is the precedent).
   Canonical ordering for hashing is unit 0133's concern, applied to the
   emitted bytes — the serde layer never reorders data.
4. **Floats ride JSON's exact round-trip.** The only floats in the chain
   are ER confidences/scores (`Resolution`, `Mention`,
   `GroundedAssertion`); `json.dumps`/`loads` round-trips Python floats
   exactly (repr-based), pinned by the fidelity tests.
5. **Strict, typed extraction.** `from_dict` uses small typed extractors
   that raise `ValueError` naming the offending key on a wrong type or a
   missing field — malformed input fails loudly here, and unit 0134 wraps
   that into the verify CLI's clean error path. Unknown extra keys are
   ignored (forward compatibility across bundle-format minors).
6. **The re-verification bridge lives here.** Two small helpers —
   `record_from_evidence(GroundedEvidence) -> EvidenceRecord` and
   `claim_from_grounded(GroundedClaim) -> Claim` — rebuild the exact
   inputs `is_supported` consumes from the serialized boundary form. A
   smoke test proves the point of the whole unit: for a grounded business
   answer, rebuild the claims and the graph from dicts alone and re-run
   `is_supported` — the verdicts must equal the recorded `verified`
   flags. (The full equality floor over all gold cases is unit 0134.)

## Scope

**In:** `tessera/bundle/__init__.py`, `tessera/bundle/serde.py`,
`tests/test_bundle_serde.py`.
**Out:** bundle format/hashing/signing, emission, CLI, verify, docs
(units 0133–0134); any change to existing modules.

## Acceptance criteria

- [ ] Graph round-trip is tuple-exact AND byte-identical
      (`to_dict → from_dict → to_dict` under canonical dumps) on all
      three committed corpora (business, devex, github_actions).
- [ ] Knowledge-base round-trip likewise.
- [ ] `GroundedResult` round-trip byte-identical for a grounded answer
      and a refusal in each domain.
- [ ] `RenderedPayload` (rendered + withheld), `ActionProposal`
      (grounded + carried refusal), and `ExecutionReceipt` (simulated
      live + the committed `data/execution/receipt.json` fixture)
      round-trip byte-identical.
- [ ] The re-verification smoke test passes (decision 6).
- [ ] Malformed input raises `ValueError` naming the key.
- [ ] Gate green; six eval lines byte-identical; no existing file
      modified.

## Eval impact

None — additive module + tests only.

## Risks / notes

- The committed receipt fixture's JSON key order differs from
  `to_dict` order; byte-identity is asserted on canonical re-dumps
  (`sort_keys=True`), not raw file bytes.
- `Claim` requires non-empty support by construction; a boundary claim
  always carries support, so `claim_from_grounded` cannot construct an
  unsupported claim — the invariant survives reconstruction.
