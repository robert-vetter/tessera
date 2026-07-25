# 0146. The Verification Gap — a conformance benchmark for agent-receipt verification

- **Phase / milestone:** ROADMAP3 Milestone 22 (the public proof). The
  largest trust-bearing unit of the act: it *grades verification
  methods*, so the honesty rules are stricter than anywhere else.
- **Issue:** —
- **Status:** approved (autonomous session; decision, prior-art findings
  and rationale recorded here per CLAUDE.md "Autonomous phase execution").

## Problem

Tessera's whole positioning rests on one sentence: *every shipping agent
receipt verifies integrity; none verifies content.* Until now that
sentence has been an **assertion backed by reading**. An assertion is
what every vendor has. This unit turns it into a **measurement anyone can
re-run**: faithful, steelmanned implementations of the verification
methods actually published in 2026, graded against a battery of attacks,
under two explicitly stated threat models, with the scorecard committed
and CI-pinned so it can never silently drift.

The output is not "we win". It is a map of *which method detects what*,
including the cases where the other methods are sufficient and Tessera
adds nothing — because a benchmark whose author always wins is marketing,
and marketing is not evidence.

## Prior art actually read (2026-07-18) — and what it changes

1. **IETF draft (ASQAV compliance receipts, July 2026)** — signed action
   receipts bound to EU AI Act obligations; verification = build payload,
   canonicalize (JCS), SHA-256, Ed25519 signature, offline check.
2. **Microsoft Agent Governance Toolkit, "Independently Verifiable
   Compliance Receipts"** — a bounded verification model of exactly three
   checks: signature validity against the declared signer key, chain
   integrity (each `previousReceiptHash` matches), and policy binding
   (`covenantHash` matches the expected policy). The proposal states
   plainly that an auditor needs no operator access — and that the
   verifier cannot independently re-derive whether the decision itself was
   correct, only that it was signed consistently.
3. **"Proof of Execution: Runtime Verification for Governed AI Agent
   Actions", Rhodes & Kang, arXiv:2607.05397 (Apr 2026)** — the closest
   prior art to this project and, read carefully, a **complement rather
   than an overlap**. PoE formalizes execution as (contract, causal event
   stream, replay context) and checks five invariants that the paper
   itself calls *syntactic predicates* — contract freshness, gateway scope,
   null-effect-on-deny, sealed commit order, and envelope closure (I5a),
   which checks only that the *declared* envelope is consistent with the
   replay context; the paper explicitly places discovery of **undeclared**
   dependencies outside I5a's scope (it enters via a deployment-assumption
   term). Deterministic replay (G5) is a guarantee about the deployed
   system under interpreter-determinism and dependency-declaration
   assumptions — not a claim-vs-evidence recomputation the validator
   performs.

**Consequence for our own claim, recorded honestly:** spec 0131's scoped
novelty claim survives but must be stated more precisely from now on.
PoE verifies *that an action was authorized, in scope, recorded and
replayable*; Tessera verifies *that the claims in an answer follow from
the evidence cited*. Orthogonal axes. The benchmark says so in the
document, and the docs stop implying that nobody has worked on
replay/attestation — they have, well, and adjacently.

## The two threat models (the load-bearing honesty)

- **T1 — outside tamperer.** Someone who does not hold the issuer's
  signing key alters a receipt in transit or at rest. **Under T1
  signatures are sufficient**: any change moves the root, and the attacker
  cannot re-sign. The benchmark shows the signature-based methods scoring
  100% here, and says so first.
- **T2 — the issuer itself** (a self-serving operator, a compromised
  key, or an agent pipeline that seals its own output). The forgery is
  produced *inside* the trust boundary and re-signed with a legitimate
  key. Every integrity/signature/policy-binding check passes it by
  construction — they verify that a record was not altered *by someone
  else*, which is not the question anyone is actually asking about an AI
  agent's answer.

> An agent's receipt is signed by the party whose honesty is in
> question. That is the whole gap, and T2 is where it lives.

## Decisions

1. **Five methods, steelmanned, source-committed** (`conformance/methods.py`),
   each a pure function `(original, mutant, threat) -> Outcome`:
   - `hash-manifest` — canonical per-leaf hashing + Merkle root recompute
     (the plain hash-chained receipt).
   - `signed-receipt` — the above plus an attested root the attacker
     cannot forge under T1 (models IETF/ASQAV Ed25519 receipts *without
     needing the optional crypto extra*: an unforgeable attested value is
     exactly what a signature provides, so the model is faithful and CI
     stays key-free).
   - `policy-bound-receipt` — signed-receipt plus a declared policy/covenant
     hash binding (models the Microsoft AGT proposal's three checks).
   - `syntactic-envelope` — declared-envelope-hash consistency plus sealed
     order (models PoE's I5a/I4 validator invariants, and *only* those:
     the paper's own scope).
   - `re-execution` — Tessera's verifier.
   Each method's docstring names the source it models and the exact scope
   the source claims for itself.
2. **Three outcomes, not two:** `DETECTED`, `MISSED`, and
   `NOT-APPLICABLE` — the last for attacks that cannot exist against a
   given design (e.g. an in-receipt policy swap against a design that
   deliberately keeps policy outside the artifact, ADR 0034). Counting an
   impossible attack as a "win" would be exactly the dishonesty this
   benchmark exists to expose.
3. **~20 attacks in five families**, reusing the CI-pinned mutation
   battery where it already exists (spec 0137) and adding chain,
   governance and declaration attacks: envelope (no re-seal), semantic
   (re-sealed), action/wire (re-sealed), chain (re-sealed, incl. the deep
   forge), and governance/declaration (`policy_swap`,
   `undeclared_dependency` — the PoE-scoped case).
4. **`tessera conformance [--json] [--threat …]`** renders the scorecard;
   `data/conformance/scorecard.json` is committed and a test pins it
   byte-identical to a fresh run (the spec-0140 no-drift pattern), so the
   published numbers cannot rot.
5. **`docs/CONFORMANCE.md`** carries the methodology, the primary-source
   citations, the steelman statement, the full per-attack table, the T1
   result stated *before* the T2 result, and the honest limits.
6. **No named-product scores, ever.** The benchmark grades *methods*, not
   vendors. Every reference implementation is ours, committed, and written
   to be as strong as the published description allows.

## The anti-strawman guarantees (test-pinned)

- **No false positives anywhere:** every method passes every honest base
  bundle under both threat models — pinned. A method that cries wolf
  would otherwise score well for the worst possible reason.
- Every reference method **detects the classic byte-level tampering it is
  designed for** (corrupted leaf, corrupted root) under both models —
  pinned. A benchmark whose baselines score zero everywhere is rigged.
- Under **T1**, `signed-receipt` and `policy-bound-receipt` detect
  **every re-sealed** attack — pinned. The gap is a T2 phenomenon and the
  tests say so.
- **Measured, correcting this spec's own first draft:** all four
  non-re-executing methods miss `extra_top_section`, not just
  `hash-manifest` — a signature over a Merkle root does not commit to the
  *section set*, so a smuggled section rides along unhashed. That is the
  exact hole Tessera's own M20/M21 audit found and fixed in its integrity
  layer; the envelope column is therefore 2/3, not 3/3, for every
  baseline. Kept as measured rather than adjusted to the prediction.
- **Tessera loses a cell, and it stays:** `stale_contract_replay` — an
  honest, unaltered receipt whose mandate expired — is MISSED by
  re-execution (a PASS is not a recency claim, BUNDLE.md's recorded
  limit) and DETECTED by the runtime-attestation method. Pinned.
- `NOT-APPLICABLE` outcomes never count toward a method's score.

## Scope

**In:** `tessera/conformance/{methods,attacks,runner}.py`, the
`conformance` CLI verb, `data/conformance/scorecard.json`,
`tests/test_conformance.py`, `docs/CONFORMANCE.md`, README + mkdocs
pointers, a MARKET.md prior-art line, and a precision fix to the public
novelty wording (ROADMAP3/BUNDLE) in light of PoE.
**Out:** running the benchmark against any third-party product (we grade
methods, not vendors); LLM-judge methods (non-deterministic, measured
separately in M22); Rekor (0138); the write-up (0141).

## Acceptance criteria

- [ ] `tessera conformance` prints a per-family scorecard for both threat
      models; `--json` round-trips; the committed scorecard is
      byte-identical to a fresh run (pinned).
- [ ] Anti-strawman pins above all hold.
- [ ] Under T2, semantic/action/chain attacks: every non-re-executing
      method MISSES all of them; `re-execution` DETECTS all of them —
      each with a named cause available.
- [ ] `undeclared_dependency` is DETECTED by re-execution and MISSED by
      `syntactic-envelope`, with the paper's own scope statement cited in
      the docs.
- [ ] Deterministic across `PYTHONHASHSEED`; stdlib-only (leak-guard); no
      network.
- [ ] Gate green; six eval lines byte-identical; frozen core + agent
      chain empty-diff; mkdocs strict green.

## Eval impact

None — additive package + CLI + docs + tests. (The faithfulness eval and
this conformance benchmark measure different things and stay separate.)

## Risks / notes

- **Overclaim is the whole risk.** Mitigations: no vendor names, T1
  stated first, `NOT-APPLICABLE` outcomes, steelman pins, committed
  reference sources, and an explicit "what this does NOT measure"
  section (it measures detection of *these* attacks on *this* format;
  the structural conclusion generalizes because a method that never
  re-executes cannot detect a re-sealed semantic edit *by construction* —
  that argument is stated as an argument, not as data).
- The PoE reading must stay fair: it is strong at what it claims
  (authorization, scope, trace integrity, replayability under stated
  assumptions) and explicitly does not claim claim-vs-evidence checking.
