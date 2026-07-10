# 0134. Offline re-executing verify — `tessera verify answer.tsb`

- **Phase / milestone:** ROADMAP3 Milestone 20, unit 3 (plan: spec 0131).
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0131). Trust-bearing —
  pre-merge 3-lens adversarial review required.

## Problem

Units 0132/0133 made the bundle reconstructible and sealed. This unit is
the differentiator itself: `tessera verify answer.tsb` — stdlib-only,
offline — must **re-derive** the bundle's verdicts from the file alone,
report the integrity layer and the semantic layer separately, and name
what broke. Everything the act may publicly claim (spec 0131) is a
property of this command.

## Decisions

1. **Two layers, always both, reported separately.**
   - *Integrity:* the 0133 re-check (`integrity_mismatches`) — proves
     the file is the file, names the exact leaf. Runs first, but a
     broken envelope does **not** suppress the semantic layer: the
     flip-a-byte demo wants both stories, and a tamperer who re-seals
     (recomputes manifest + root — trivial until signatures land in
     unit 0135) makes integrity pass while semantics catch the lie.
   - *Semantic:* re-execution of the verification from the packaged
     evidence, per the taxonomy below.
2. **Semantic re-execution is TWO checks, not one.**
   - *(a) Claim-vs-evidence re-verification* — for every recorded claim,
     rebuild the core `Claim` + the graph via `serde` and re-run the
     eval's `is_supported` under the pinned shape set; compare with the
     recorded `verified` flag.
   - *(b) Answer re-derivation* — re-run the domain's deterministic
     router over the packaged graph + knowledge base
     (`dom.route(question, graph, kb)` → `serialize_answer`) and require
     the result to match the recorded one: same mode
     (grounded/refused), same route kind, same claim texts in order,
     same per-claim verdicts, same refusal reason.
     **Why (b) exists — the claim-swap attack:** without it, an attacker
     replaces the recorded claims with *different, individually true,
     re-derivable* claims (e.g. from another question in the same
     corpus) and re-seals; check (a) alone would pass a record whose
     answer no longer belongs to its question. (b) binds
     question → answer → claims to the packaged corpus. It is also what
     makes a **refusal** bundle re-derivable (spec 0131 D4): the corpus
     itself re-yields the refusal and its reason.
3. **The verdict taxonomy (spec 0131 D3), decided per bundle then per
   claim:**
   - `NOT-EVALUABLE` — the installed engine cannot honestly judge:
     unknown domain, engine version mismatch, or shape-identifier
     mismatch (ADR 0031 §5: identifier equality **plus** version
     equality is the only combination read as "same grammar"). The
     message names both sides. No re-derivation is attempted — a
     verdict under a different grammar would be a different verdict
     wearing the same name.
   - `INTEGRITY-ONLY` — the evidence closure is not fully packaged
     (any `evidence_closure.kind` other than `full-graph-snapshot`):
     hashes are checked, content cannot be re-derived, and the output
     says exactly that. An unknown closure kind can only ever degrade
     here, never upgrade (ADR 0031 §3).
   - `RE-DERIVED` — re-execution ran; each claim reports its re-derived
     verdict, the recorded verdict, and whether they match. The
     interesting states: recorded-true-but-re-derives-false (the
     flip-a-byte catch: tamper or false claim, cause names the claim)
     and recorded-false-but-re-derives-true (a flipped stored verdict).
     A claim recorded unverified that re-derives unverified is a
     *faithful record of an unverified claim* — reported, not a
     mismatch (unreachable on the committed corpora, whose faithfulness
     floor is 1.0; the code path is tested at function level and the
     taxonomy documents it).
4. **Structural invariants are checked before re-derivation** and
   violations are semantic failures: exactly one of grounded/refused;
   refused ⇒ no claims ∧ a refusal reason; grounded ⇒ claims ∧ no
   refusal.
5. **Exit codes (spec 0131 D3), precedence 4 > 2 > 3 > 0:**
   - `4` — envelope unreadable or broken: malformed JSON, wrong format
     major, missing sections, or any integrity mismatch.
   - `2` — semantic failure: a claim disagreement, an answer
     re-derivation divergence, or a structural violation.
   - `3` — degraded, nothing failed: `NOT-EVALUABLE` or
     `INTEGRITY-ONLY` bundle, or an honestly-unverified claim present.
   - `0` — integrity intact, every claim re-derived and matching and
     verified, the answer re-derives (for a refusal: the refusal
     re-derives).
6. **Pure function + thin CLI.** `verify_bundle(bundle: dict) ->
   VerifyReport` (dataclass with `to_dict()`); `tessera verify <file>
   [--json]` wraps file IO and formatting; the front door reserves
   `verify` (completing the pair spec 0133 started; same recorded
   residual). The verify path imports only stdlib + the engine's own
   modules — no extras, no network (the existing leak-guard pattern
   extends to it).
7. **The foil ships with the demo.** `scripts/foil_integrity_only.py` —
   the deliberately naive ~20-line checker that re-computes manifest +
   root and prints "intact": what integrity-only verification (the
   market default, spec 0131's prior-art finding) sees. Used by
   `docs/BUNDLE.md`'s flip-a-byte walkthrough, which tampers a packaged
   record, re-seals, and shows the foil pass while `tessera verify`
   names the broken claim.
8. **`docs/BUNDLE.md`** documents: the two layers, the taxonomy, exit
   codes, the format reference, engine pinning/version drift, measured
   bundle sizes, and honest limits — scoped strictly by the fixed claim
   and caveats (spec 0131 D12): the envelope is not the novelty; claims
   outside the engine's grammars fall to containment; unsigned bundles
   prove integrity, not origin (signatures are unit 0135).

## Scope

**In:** `tessera/bundle/verify.py`, verify entry in
`tessera/bundle/cli.py`, the `verify` dispatch line in `tessera/cli.py`,
`scripts/foil_integrity_only.py`, `docs/BUNDLE.md` (+ mkdocs nav),
`tests/test_bundle_verify.py`.
**Out:** signatures (0135), action-chain verification (0136), the
mutation battery + floors artifact (0137), Rekor (0138).

## Acceptance criteria

- [ ] Intact bundles: exit 0 for a grounded answer and a refusal in
      each committed domain.
- [ ] **Milestone floor preview:** across every gold case of all three
      committed batteries, emit → verify in-process reports 100%
      re-derivation equality (the standing CI artifact is unit 0137;
      this unit pins the same property as a test).
- [ ] Flip-a-byte, re-sealed: integrity intact, the dependent claim
      named, exit 2 — and the foil script prints "intact".
- [ ] Flip-a-byte, not re-sealed: exit 4 with the exact leaf named,
      semantic layer still reported.
- [ ] Claim-swap (re-sealed): caught by answer re-derivation, exit 2.
- [ ] Verdict flip, question swap, refusal-reason edit (re-sealed):
      exit 2 with causes named.
- [ ] Version/shape/domain mismatch: `NOT-EVALUABLE`, both sides named,
      exit 3. Unknown closure kind: `INTEGRITY-ONLY`, exit 3.
- [ ] Verify-path import guard: no extras, no `mcp`/`hdbcli`/embedding
      imports (existing leak-guard pattern).
- [ ] Gate green; six eval lines byte-identical; existing files touched:
      `tessera/cli.py` (verify dispatch) and `tessera/bundle/cli.py`
      only.

## Eval impact

None — additive verification surface; the eval harness is unchanged
(its `is_supported` is *consumed*, not modified).

## Risks / notes

- **(b) binds verify to the router's determinism across versions** —
  acceptable because `NOT-EVALUABLE` already requires version equality
  before any re-derivation; recorded plainly in BUNDLE.md.
- The claim-vs-evidence check (a) runs on the *recorded* claims with
  their *recorded* citations — evidence text comes from the packaged
  closure via the record leaves, so (a)+(b) together cover both "are
  the citations honest" and "is this the corpus's answer".
- An attacker editing `engine.claim_shapes`/`tessera_version` and
  re-sealing downgrades the bundle to `NOT-EVALUABLE` (exit 3) — a
  *visible* degradation, never a false PASS; documented in BUNDLE.md.
