# 0143. Chained trust bundles — the audit trail for agent pipelines

- **Phase / milestone:** ROADMAP3 Milestone 22 (the public proof) —
  an added unit in the 0142 pattern. Trust-bearing (it extends the
  verifier's guarantee across bundles) → adversarial self-review before
  merge, attack classes test-pinned.
- **Issue:** —
- **Status:** approved (autonomous session; decision and rationale
  recorded here per CLAUDE.md "Autonomous phase execution").

## Problem

2026's agent systems are pipelines: one agent's output is the next
agent's input. Every shipping receipt system — including Tessera until
this unit — attests *single* decisions; what travels **between** agents
is unverified text, so a pipeline's audit trail is only as strong as its
weakest hand-off. Tessera already owns the missing primitive (offline
re-execution). This unit makes it **compose**: a verified bundle becomes
first-class *evidence* for the next answer, and one offline command
re-executes the entire chain.

> To forge a chain, you must forge one link's own re-execution — and the
> forged-bundle challenge (spec 0140) exists to show you cannot.

**Why this unit now (the strategy decision, recorded):** the maintainer
asked for the feature a design-partner audience would rate highest. The
candidates considered: a CI verification action (packaging, low novelty),
a browser verify pane on the live Space (touches the deployed demo while
the maintainer is away), evidence-drift diffing (niche), and chaining.
Chaining wins because it extends the *confirmed-empty* re-execution slot
(no shipping system re-checks content) **transitively to multi-agent
pipelines** — the axis the market is moving on — while staying offline,
deterministic, additive, and demonstrable in one command from a clean
clone. The others are recorded as future work.

## Decisions

1. **Cite only what re-verifies.** A chain bundle's corpus is derived
   exclusively from upstream bundles' verifier-passing claims: emission
   runs the full `verify_bundle` on every upstream and **refuses** (named
   reason) unless the verdict is PASS; only claims that are recorded
   verified *and* re-derived become records. Refusal-only upstreams →
   emission refuses ("nothing citable").
2. **Closure kind `chain-snapshot`** (format minor 1.1 as a per-file
   feature level — single-decision bundles keep declaring 1.0 so the
   committed challenge artifacts stay byte-stable; ADR 0033): `evidence_closure = {kind, graph, kb, upstream: [sealed
   upstream bundles, embedded whole]}`. The integrity manifest gains one
   leaf per upstream, named `upstream:<root>`, hashing the embedded
   bundle; duplicate roots are rejected. The root thereby commits to the
   upstream *set by root* — the chain is a hash-DAG with re-execution on
   top — and the bundle stays self-contained (verify needs the one file).
   `full-graph-snapshot` closures must NOT carry `upstream`; section-set
   checks are kind-aware.
3. **Derived evidence is verbatim.** Record id `chain:<root12>:c<index>`;
   `Origin(source="bundle:<root>", locator kind "bundle-claim" with parts
   root/claim, ingested_at="at-upstream-seal")` — deterministic, no
   wall-clock (ADR 0031's byte-stability holds). Record text = the
   upstream claim text, byte-for-byte: no paraphrase, so the generic
   containment grammar re-derives chain claims honestly.
4. **The chain route is the frozen core, called not modified:**
   `tessera.retrieval.answer` (BM25 + principled refusal) over the
   derived corpus; `Route(kind="chain")`. The chain declares **one claim
   grammar** (`chain_citation`, carried in `engine.claim_shapes` like any
   vertical's, ADR 0011): a claim is a *verbatim citation* of exactly one
   bundle-claim record in the packaged corpus. It owns the verdict for
   such claims so the generic grammars (notably the shared-fragment
   recomputation) do not re-argue an upstream claim against the chain
   corpus, where the upstream's raw sources rightly do not exist — the
   deeper truth is re-established by the recursive upstream verification,
   which is the design point. (Surfaced by the first live run: upstream
   shared-fragment claims scored UNSUPPORTED at chain level under the
   generic grammars; the citation grammar is the honest fix, not a
   special-case suppression.) The chain answer *cites* upstream findings
   — it computes nothing new (no cross-bundle aggregation/synthesis in
   v1; named future work).
5. **Verify grows a chain branch inside the bundle layer** — the domain
   registry (`agent/grounded.py`) and the whole agent chain stay
   byte-identical. For `domain == "chain"`: the taxonomy gate replaces
   registry membership with bundle-native rules (recorded claim shapes
   must be `[]`; version pin unchanged), and re-execution adds, on top of
   the existing envelope/structural/claims/answer machinery:
   - (i) every embedded upstream re-verifies **recursively** (full
     `verify_bundle`); a non-PASS propagates as a named semantic failure
     (`upstream <root12>: <cause>`) — never a rubber stamp of recorded
     verdicts;
   - (ii) every kb record must map to an embedded upstream root + claim
     index, byte-match that claim's text, and that claim must have
     re-derived in the upstream's own re-execution;
   - (iii) an embedded-but-uncited upstream is still fully verified (it
     is sealed content);
   - (iv) answer re-derivation re-runs the chain route over the packaged
     corpus with canonical-bytes equality, same divergence naming.
   `VerifyReport` gains an additive `upstreams` field (root, verdict per
   link) and `render_report` prints the chain summary.
6. **Depth and cycles.** Recursion is structural (a chain can cite a
   chain; tested at depth 2). Cycles are impossible by construction —
   embedding requires the upstream's final sealed bytes, so no bundle can
   contain its own root; documented with the hash argument, no
   pretend cycle-detector.
7. **Committed demo:** `scripts/build_chain_demo.py` (deterministic)
   builds a devex RCA bundle + a business comparison bundle and chains
   them into `data/chain/brief.tsb` (committed); a byte-identity test
   pins no drift (the spec-0140 pattern). `docs/CHAIN.md` carries the
   walkthrough (verify PASS → flip a byte inside an embedded upstream →
   exit 4 → the full re-seal attack → exit 2, upstream named) and the
   honest-limits section.
8. **Signing composes, unchanged:** the chain root signs like any root;
   embedded upstream signatures travel and are re-checked during the
   recursive verification.
9. **`audit`/`explain` must work on chain bundles** (tested; the Art. 12
   mapping rows remain literally true — the file carries question,
   claims, evidence, verdict). Extending the Auditability Floor with
   chain mutation classes is **named future work**: the attack classes
   are covered by this unit's adversarial tests, outside the CI-pinned
   floor, honestly stated.

## Scope

**In:** `bundle/chain.py`, `format.py` (kind-aware closure/manifest,
minor 1.1), `verify.py` chain branch + report extension, `bundle/cli.py`
`chain` verb + front-door help, `tests/test_bundle_chain.py`,
`scripts/build_chain_demo.py`, `data/chain/`, `docs/CHAIN.md`,
BUNDLE/README/mkdocs pointers, ROADMAP3 stale-date fix (the deferred
timeline, drift found during recon).
**Out:** floor extension (named), MCP exposure of chain emission
(named), cross-bundle computation/aggregation (named), Rekor (0138),
any "works with any agent" claim.

## Acceptance criteria

- [ ] `bundle chain` over a devex RCA bundle + a business comparison
      bundle → `tessera verify` PASS from the file alone; report shows
      each upstream re-verified.
- [ ] **Deep-forge attack** (tamper evidence inside an embedded
      upstream, re-seal the upstream, re-embed, re-seal the chain — the
      strongest attacker, full re-seal powers at every level) → FAIL,
      upstream root + cause named.
- [ ] Cited-claim mismatch, upstream swap, missing upstream (all fully
      re-sealed) → FAIL, named. Byte-flip anywhere incl. inside an
      embedded upstream → exit 4.
- [ ] Non-PASS upstream at emission → refused, named. Refusal-only
      upstreams → refused ("nothing citable").
- [ ] Chain-of-chain (depth 2) verifies PASS.
- [ ] Emission byte-identical across `PYTHONHASHSEED` values
      (subprocess); committed demo byte-identity pinned.
- [ ] `audit` and `explain` render chain bundles without breakage.
- [ ] Gate green; six eval lines byte-identical; frozen core AND agent
      chain empty-diff; mkdocs strict green.

## Eval impact

None — additive command + format extension + tests + docs.

## Risks / notes

- **Overclaim risk:** "multi-agent audit trail" must always be scoped to
  *Tessera bundles* (agents participate by exchanging bundles via
  CLI/MCP); never "verifies any agent's output" (Act 3 will-not-do).
- **Size:** embedded upstreams grow the file (measured in the demo doc;
  business 404 KB dominates). Acceptable for v1; delta encoding is
  non-goal.
- The recursive verify cost is linear in links; depth in practice is
  small. The backstop (no uncaught exception) covers the new paths.
