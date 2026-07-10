# Roadmap — Act 3: Verifiable Audit (July 2026)

Act 1 ([ROADMAP.md](ROADMAP.md)) built and measured the trust substrate.
Act 2 ([ROADMAP2.md](ROADMAP2.md)) made it a product: a hosted demo, BYO
data doors, the Faithfulness Floor benchmark, MCP registry artifacts, a
launch, and the SAP track (real SALT run, HANA measurements). The launch
landed at the statistical median for its category — recorded honestly in
[STATUS.md](STATUS.md); the positioning and the pilot wedge survive it
unchanged.

Act 3 builds the thing the receipt story was always pointing at.

## The thesis

Since Milestone 15, every Tessera action ends in a receipt linking the
executed request back through verifier-passing claims to evidence
records. But that receipt is only checkable where it was made. Meanwhile
the 2026 market converged on signed agent receipts, hash-chained audit
logs, and Merkle evidence bundles — systems that prove a log was **not
altered**, and concede (several in writing) that a perfectly hash-chained
transcript of hallucinations verifies flawlessly. Integrity is solved;
**truth is not checked**. An independent 2026 conformance test of four
agent-governance tools states it verbatim: none performs re-execution
verification — all rely on signature and hash-chain validation.

Tessera owns the missing half already: a deterministic, dependency-free
verifier that recomputes claims against evidence instead of judging
them. Act 3 puts that verifier inside a portable artifact:

> **The trust bundle:** one signed file per answer or action — evidence
> records → claims → verdicts → human approval → exact wire request →
> receipt — that a stranger re-checks **offline by re-executing the
> verification**: `tessera verify answer.tsb` re-derives every verdict
> from the file alone. Flip one byte of one packaged record and exactly
> the dependent claim (and the action it justified) fails, with a named
> cause. A signature check cannot do that; that is the point.

The scoped novelty claim, its mandatory caveats, and every load-bearing
design decision are fixed in [spec 0131](https://github.com/robert-vetter/tessera/blob/main/specs/0131-verifiable-audit-plan.md)
— public copy may not exceed them.

The timing is dated: the EU AI Act's high-risk record-keeping and
human-oversight obligations (Articles 12 and 14) apply from
**2026-08-02**, with both candidate technical standards still drafts.
Act 3 ships a field-level **mapping** to those articles — a mapping,
never a compliance claim.

**Positioning (Act 2's line, extended one clause):**

> The agent can only say what it can prove — and only do what you
> approve. **And now the proof travels:** every answer can leave as one
> signed file a stranger re-checks by re-running the verification,
> offline.

## The build (three milestones)

Discipline unchanged (CLAUDE.md): spec → branch → gate → PR → CI-green →
squash-merge; ADRs for hard-to-reverse choices (bundle format, signing
dependency); adversarial pre-merge review on the trust-bearing units;
the six existing eval lines stay byte-identical throughout; the frozen
core stays frozen (empty-diff audit at each milestone close).

### Milestone 20 — the bundle re-executes

*What becomes true:* `tessera bundle "<question>" --domain <d> -o
answer.tsb` emits a trust bundle for any committed domain;
`tessera verify answer.tsb` — stdlib-only, offline — reconstructs the
evidence and **re-derives** every claim verdict from the file alone;
tampering with any packaged record flips exactly the dependent claim to
`RE-DERIVED FAIL` with a named cause, demonstrated against a deliberately
naive hash-only foil.

Units (specs 0132–0134): the serialization round-trip layer, the bundle
format + emission (ADR 0031: canonical bytes, Merkle root, evidence
closure, the verdict taxonomy `RE-DERIVED` / `INTEGRITY-ONLY` /
`NOT-EVALUABLE`, engine-version pinning), the offline re-executing
verifier + `docs/BUNDLE.md` with the flip-a-byte walkthrough.

*Done when:* re-derivation equality with the live harness is 100% across
all gold cases of all three committed batteries; the flip-a-byte demo is
recorded; tag `milestone-20`.

### Milestone 21 — sealed and measured

*What becomes true:* bundles carry an Ed25519 signature (signing is an
optional extra; **verification stays stdlib-only** via an in-repo RFC
8032 implementation); action bundles link receipt → approved request →
claims → evidence and re-verify offline; and the act's own benchmark
exists — the **Auditability Floor**: 100% re-derivation equality and
100% mutation detection (≥10 tamper classes, each naming its broken
claim or link), CI-pinned like the Faithfulness Floor, plus a 3-OS
determinism matrix in CI, because one spurious mismatch on a stranger's
laptop would kill the whole claim.

Units (specs 0135–0137). *Done when:* both floors are green and pinned;
the matrix is green; tag `milestone-21`.

### Milestone 22 — the public proof

*What becomes true:* the repository carries a standing challenge — two
downloadable bundles, one honest, one a cryptographically perfect,
internally consistent **fake**, produced by a committed, reproducible
forging script — and one offline command separates them. Optional,
each behind a maintainer decision: bundle roots anchored in the public
Sigstore transparency log; a recorded one-shot where a pinned LLM-judge
evaluator scores the forged bundle's claims high while the deterministic
verifier fails them. `docs/COMPLIANCE.md` maps bundle fields to EU AI
Act Articles 12(2)/14 and the IETF receipt drafts. The write-up and
README tell exactly the scoped story and nothing more.

Units (specs 0138–0141). *Done when:* a stranger can run the challenge
from a clean clone; every public sentence traces to the fixed claim;
tag `milestone-22`.

## What Act 3 will NOT do

- **No LLM anywhere in the trust path** — the judge-model contrast is a
  one-shot measurement of the *subject*, never a component.
- **No zero-knowledge proofs, no TEEs** — out of solo scope and not
  needed for the claim; re-execution over packaged evidence is the
  design point.
- **No verification surface for arbitrary text.** Bundles carry claims
  in the engine's checkable grammars; "verify any LLM output" is
  LLM-judge territory by another name and is out.
- **No compliance claims** — mappings only, standards are drafts.
- **No claim beyond the fixed sentence** in spec 0131 — the envelope
  (signing, Merkle, transparency logs, mutation batteries) is crowded
  prior art and is never presented as the novelty.
- **No SALT-derived values** in any bundle, fixture, or challenge
  artifact (gated CC-BY-NC-SA data vs MIT repo).

## Success criteria (end of Act 3)

1. The acceptance criteria of spec 0131, all checked.
2. `milestone-20/21/22` tagged; STATUS current at every wrap.
3. The Auditability Floor is a standing, CI-pinned artifact that can
   fail, beside the Faithfulness Floor.
4. The challenge is live in-repo and reproducible by a stranger.
5. The write-up states what is new, what is envelope, and what was
   measured — auditable against the prior-art map.

## Maintainer decisions (everything else runs autonomously)

1. **Q1 — Rekor:** post demo-bundle roots to the public Sigstore log
   (free, external, public)? Until yes: client ships fixture-tested
   with a staged runbook, nothing published.
2. **Q2 — LLM-judge one-shot:** small API spend + pinned judge config
   for the recorded RAGAS-vs-verifier measurement? Until yes: script
   staged, no recorded run.
3. **Q3 — technical report:** stage an arXiv-ready report alongside the
   WRITEUP addendum? Publication is the maintainer's act either way.

## Risks

- **The closure/commitment design is the hinge** (spec 0131 D3/D4): a
  `RE-DERIVED` verdict on unpackaged evidence would silently collapse
  the differentiator — closed by construction in Milestone 20 and
  attacked in review, not deferred.
- **Cross-machine byte determinism** — guarded by the proven canonical
  pattern, a strings+Decimal data model, and the CI matrix.
- **Version drift** — bundles pin engine + shape-set identifiers and
  degrade to `NOT-EVALUABLE`, visibly, never wrongly.
- **Attention is not guaranteed.** Act 2's launch met the category
  median; this act's public artifact is built to be *attackable*
  (challenge, floors, foil) rather than merely announced — but the
  fallback remains what it was: the pilot wedge and the recorded,
  auditable build.
