# 0131. Act 3 plan — verifiable audit: trust bundles a third party re-executes

- **Phase / milestone:** ROADMAP3 (Act 3) — Milestones 20–22. This spec is
  the track plan: it fixes the unit breakdown, the load-bearing decisions,
  and the honesty boundaries before any code, so the whole act can run
  autonomously per CLAUDE.md. Unit specs 0132–0141 are **reserved here**
  and land in their units' PRs, before code (specs/README.md ledger rule).
- **Issue:** —
- **Status:** approved (autonomous mode; decisions recorded below).

## Problem

Tessera's action layer already ends in a receipt: the executed request is
linked back through verifier-passing claims to the evidence records
(Milestones 13–15, ADR 0024/0025). But the receipt — like every answer —
is only checkable *in situ*: you must be on the machine, with the corpus,
running the engine. A stranger (an auditor, a reviewer, a counterparty)
cannot take Tessera's word anywhere.

Meanwhile the market converged on exactly the wrong half of this problem.
A 2026 survey of shipping agent-receipt systems (documented with sources
in the MARKET.md addendum planned as unit 0141, re-verified before
publication) shows a crowded field — signed action receipts, hash-chained
audit logs, Merkle evidence bundles, transparency-log anchoring, IETF
draft formats — that all verify **integrity**: the log was not altered.
None verifies **content**: whether the claims in the log were actually
supported by the evidence they cite. Several of these systems concede in
writing that a perfectly hash-chained transcript of hallucinations passes
their verification. An independent 2026 conformance test of four agent
governance tools states the gap verbatim: *"none of the tested tools
perform re-execution verification; all rely on signature and hash-chain
validation."*

Tessera is one step from closing that gap, because the hard part already
exists: a deterministic, dependency-free verifier that **recomputes**
claims against evidence (`is_supported`, the claim-shape grammars) rather
than judging them. What is missing is only the portable envelope: a
single file that carries the full chain — evidence → claims → verdicts →
approval → wire request → receipt — such that `tessera verify` on a
stranger's machine, offline, **re-derives** every verdict from the file
alone instead of checking a signature.

The regulatory timing is real and dated: the EU AI Act's high-risk
obligations (Article 12 record-keeping, Article 14 human oversight) apply
from **2026-08-02**, and both candidate technical standards (prEN
18229-1, ISO/IEC DIS 24970) are still drafts. Act 3 ships a mapping to
those articles — a mapping, never a compliance claim (decision D11).

## The claim this act is allowed to make (fixed verbatim)

All public copy for this act derives from this sentence and must not
exceed it:

> Tessera trust bundles are a portable, signed record of an AI agent's
> answer or action whose claim-level verdicts a third party re-derives
> **offline by re-executing deterministic claim-vs-evidence verification**
> — recomputing aggregates and containment against the evidence packaged
> in the bundle itself. Existing receipt systems verify signatures, hash
> chains, and Merkle proofs (integrity); a perfectly hash-chained
> transcript of hallucinations passes them. It fails here, and the
> verifier names the claim that broke.

Mandatory caveats, discovered in the 2026-07-10 prior-art search and
binding on every public document:

1. **The envelope is not novel.** Signed Merkle bundles, offline CLI
   verifiers, transparency-log anchoring, mutation-battery conformance
   corpora, and EU-AI-Act field mappings all exist in shipping systems.
   The novelty is exactly the semantic re-execution core; copy that
   leads with the envelope overclaims.
2. **Recompute-style verification exists in other domains** (program
   conformance: proof bounds, cost recomputation from signed traces).
   The claim is scoped to *claims-vs-evidence semantics of agent answers
   and actions* — never "the first verifier that recomputes."
3. The measurement artifact is "the first benchmark whose **measured
   property** is third-party semantic re-derivability of claim
   verdicts" — never "the first executable benchmark" (conformance
   corpora with mutation batteries exist at the integrity layer).
4. Competitor names, star counts, and quotations are re-verified with
   citations on the day any public document ships (CLAUDE.md
   no-overclaim rule).

## Recorded decisions

**D1 — Name, placement, surface.** The artifact is the **trust bundle**,
file extension `.tsb` (JSON inside; the extension marks the contract).
New package `src/tessera/bundle/` — additive consumers of existing seams
only; the frozen core (ADR 0008) is untouched and each milestone close
repeats the empty-diff audit. CLI via the existing front door (spec 0117
dispatch): `tessera bundle …` and `tessera verify …`.

**D2 — Verification is re-execution.** `tessera verify <file>` re-runs
`eval.metrics.is_supported` with the domain's claim shapes over objects
reconstructed **from the bundle alone**. The verify path is
stdlib-only — no network, no optional extras — so "a stranger re-checks
it offline" is literally true of a clean `uv sync` clone.

**D3 — Verdict taxonomy (the honesty core).** Per claim, verify reports
exactly one of:

| Verdict | Meaning |
|---|---|
| `RE-DERIVED PASS` | verdict recomputed from packaged evidence; supported |
| `RE-DERIVED FAIL` | recomputed; **not** supported (tamper or false claim) |
| `INTEGRITY-ONLY` | evidence committed (hash) but not packaged (e.g. redacted field) — content **not** re-checked |
| `NOT-EVALUABLE` | claim shape or engine version unknown to the installed verifier |

A claim whose evidence closure is not fully packaged can never receive a
`RE-DERIVED` verdict — this rule is what keeps the headline claim true on
redacted/enterprise data instead of quietly degrading to the
integrity-only guarantee the competitors are dinged for. Exit codes:
`0` all re-derived pass · `2` any re-derived fail · `3` degraded
(integrity-only / not-evaluable present, none failed) · `4` envelope
broken (root or signature mismatch). The bundle-level verdict is the
worst class present, and the human-readable output counts each class.

**D4 — Evidence closure: v1 packages the full graph snapshot.** The
committed corpora are small; whole-graph claim shapes
(`superlative_conclusion`, `compare_conclusion` — recomputed over the
WHOLE graph per spec 0019) and refusal re-derivation (ambiguity is a
graph property) therefore work honestly in v1. A bundle of cited-records
only would let a malicious bundler omit the larger customer and make a
false superlative "verify" — that failure mode is closed by
construction, not by policy. Cited-only slimming for large corpora is
named future work; the taxonomy (D3) still lands in v1, exercised by a
redacted-bundle fixture that must come out `INTEGRITY-ONLY`.

**D5 — Canonical bytes.** `bundle/canonical.py` generalizes the proven
`_canonical_request` pattern (`agent/execution.py`: sorted keys, fixed
separators, UTF-8). Leaves are sha256 over each record's canonical
bytes; the root is a Merkle tree over sorted leaves. The data model is
strings + `Decimal` (floats appear only in ER confidences, serialized by
the existing repr convention and pinned by fidelity tests), so
cross-machine byte stability is a tested property, not a hope. We do
**not** claim RFC 8785 (JCS) conformance — the exact canonicalization is
specified in ADR 0031 and is deliberately smaller than JCS.

**D6 — Version pinning.** Every bundle records `tessera_version`, a
bundle-format major version, the domain name, and the identifiers of the
claim-shape set that judged it. Verify resolves shapes from the
*installed* engine; a mismatch degrades those claims to `NOT-EVALUABLE`
with a message naming both versions. Verdicts always state the engine
version that re-derived them — a bundle is a record of *what version X
could re-derive*, and pretending otherwise would rot silently across
releases.

**D7 — Signing.** Ed25519 over the root. **Signing** requires the new
optional extra `sign` (dependency chosen in ADR 0032; default proposal
PyNaCl) — consistent with the `cloud`/`salt`/`agent` extras pattern.
**Verification** is an in-repo pure-Python RFC 8032 implementation
(slow is fine; test vectors from the RFC), so D2's stdlib-only verify
claim survives. Unsigned bundles are legal and labeled `UNSIGNED`
(integrity = root hash only). Keys are generated by `tessera bundle
keygen`, live under `var/keys/` (gitignored), and never enter CI.

**D8 — Transparency anchoring is opt-in and deferred-by-default.**
`--anchor` posts the bundle root to the public Sigstore Rekor log
(stdlib REST client) and stores the entry UUID + inclusion proof in a
sidecar. v1's offline check recomputes inclusion-proof hashes against
the stored checkpoint and says exactly that — it does **not** verify the
checkpoint signature (that needs non-stdlib ECDSA; documented limit).
Anchoring publishes to an external public service, so the **recorded**
public run is a maintainer decision (question Q1); the unit ships the
client, tests against recorded fixtures, and a staged one-shot runbook
either way (the S2/HANA pattern).

**D9 — The Auditability Floor (the measured artifact).** Mirrors the
Faithfulness Floor pattern (spec 0122, `eval/benchmark.py`): a runner +
a CI-pinned generated doc block in `docs/AUDITABILITY.md`, floors that
can actually fail:

- **Re-derivation equality, floor = 100%:** for every gold case across
  the three committed batteries, emit a bundle, verify it offline in a
  subprocess, and require verdict equality with the live harness.
- **Mutation detection, floor = 100%:** a deterministic mutation battery
  (≥10 classes: evidence value edit, evidence record omission, claim
  edit, recorded-verdict flip, approval strip, wire-request byte edit,
  leaf reorder, root mismatch, signature mismatch, engine-version spoof)
  where every mutant must produce the correct non-PASS class **and name
  the broken claim or link**.
- **Cross-platform determinism:** a new CI job runs the bundle test
  subset on a 3-OS × supported-Python matrix (ubuntu/macos/windows ×
  3.12/3.13; exact set fixed in unit 0137). The single-job gate is
  unchanged — the matrix guards byte determinism only, because one
  spurious mismatch on a stranger's laptop kills the whole claim.

**D10 — The LLM-judge contrast is a one-shot measurement, not a
dependency.** A staged script scores the forged challenge bundle's
claims with exactly one pinned evaluator (RAGAS faithfulness,
version-pinned, judge configuration documented in full) and records the
result next to the deterministic verdicts. The LLM is the measured
**subject**; it attests nothing (the project's standing rule). Requires
API spend and a judge key — maintainer question Q2; staged and
fixture-tested either way, never in CI.

**D11 — Compliance language.** `docs/COMPLIANCE.md` maps bundle fields
to EU AI Act Article 12(2) and Article 14 concepts and to the IETF
receipt-draft field sets — tables, one row per field. The words
"compliant," "certified," and "regulator-adequate" are banned; the doc
opens by stating that both candidate standards are drafts. Every
external citation is re-verified the day the doc ships.

**D12 — Data hygiene.** No SALT-derived values in any bundle, fixture,
or challenge artifact, ever (CC-BY-NC-SA gated data vs MIT repo — spec
0130's rule). Challenge and demo bundles come from the synthetic
corpora only. The maintainer's application/launch material stays local
(`launch/` publish rule); this plan and all public docs describe
audiences as auditors, reviewers, and the research community.

## Unit breakdown

Every unit: its own spec (number reserved below) in its PR before code;
branch → gate (`scripts/gate.sh`) → PR → CI-green → squash-merge; six
eval lines byte-identical throughout; trust-bearing units (0134, 0136,
0140) get the 3-lens adversarial pre-merge review.

### Milestone 20 — the bundle re-executes (tag `milestone-20`)

*What becomes true:* one command emits a trust bundle for any committed
domain; a second command, on evidence reconstructed from the file alone,
re-derives every verdict; flipping one byte of one packaged record flips
exactly the dependent claim to `RE-DERIVED FAIL` with a named cause.

1. **0132 — serialization round-trip.** `bundle/serde.py`: `from_dict`
   reconstruction for the chain — `Origin`/`Locator`/`EvidenceRecord`/
   `Claim` (`grounding.py`), `Node` + full `KnowledgeGraph` snapshot
   (`graph.py`, incl. resolutions/mentions with confidences and
   reasons), `GroundedEvidence`/`GroundedClaim`/`GroundedResult`
   (`agent/grounded.py`), `RenderedPayload` + slots
   (`agent/payloads.py`), `ActionProposal` (`agent/actions.py`),
   `ExecutionReceipt` (`agent/execution.py`). Nothing in those modules
   changes; serde consumes their `to_dict` output. Tests: for all three
   committed corpora and the committed receipt fixture,
   `to_dict → from_dict → to_dict` is byte-identical under canonical
   dumps; graph rebuild is tuple-exact (the `platform/kg.py`
   losslessness test is the precedent).
2. **0133 — bundle format + emission (ADR 0031).** `bundle/canonical.py`
   (D5), `bundle/format.py` (schema, leaves/root, version + shape-set
   pinning per D6, the D3 taxonomy fields), `bundle/emit.py` (wraps
   `agent.grounded.ground()` + `serialize_answer()` + the emission-time
   verdicts of `verify_claims()`; packages the graph snapshot per D4).
   CLI: `tessera bundle "<question>" --domain business|devex|github_actions
   -o answer.tsb`. ADR 0031 records: canonical-bytes spec, Merkle
   construction, closure rule, taxonomy, version pinning, `.tsb`
   contract. Tests: emission on all three domains; root stability
   across two interpreter processes (hash-seed variance); schema
   round-trip.
3. **0134 — offline verify + the flip-a-byte demo.** `bundle/verify.py`
   + `tessera verify <file>`: recheck leaves/root, reconstruct via
   serde, re-run `is_supported` with the pinned shape set, emit D3
   verdicts and exit codes. First tamper tests: one mutation per bundle
   section, each naming its broken claim/link.
   `scripts/foil_signature_check.py`: the deliberately naive ~10-line
   hash-only verifier used in the docs walkthrough as the contrast.
   `docs/BUNDLE.md`: the concept, the format table, the taxonomy
   semantics, version pinning, honest limits (D4 size note, D6 drift),
   and the flip-a-byte walkthrough. **Adversarial review.**
   Milestone close: re-derivation equality over all gold cases recorded
   in STATUS; empty-diff audit; tag.

### Milestone 21 — sealed and measured (tag `milestone-21`)

*What becomes true:* bundles carry a checkable signature without
breaking the stdlib-only verify path; action bundles link receipt →
approved request → claims → evidence and re-verify offline; the
Auditability Floor exists, is CI-pinned, and can fail.

4. **0135 — signing (ADR 0032).** `bundle/signing.py` (emit side, extra
   `sign`), `bundle/ed25519_verify.py` (pure-Python RFC 8032 verify with
   RFC test vectors), `tessera bundle keygen` (keys under `var/keys/`,
   gitignored). Signed/unsigned both legal, labeled (D7). Tamper class:
   signature mismatch, key mismatch.
5. **0136 — action bundles.** Extend emit/verify to the action chain:
   proposal → rendered payload with per-slot provenance → approval
   record → canonical request bytes (reuse `_canonical_request`) →
   receipt. Verify re-derives each slot value's provenance to a
   re-derived claim and checks the receipt's request hash equals the
   canonical bytes' hash. Fixture: the committed scrubbed real receipt.
   **Adversarial review.**
6. **0137 — the Auditability Floor.** `eval/auditability.py` + console
   script `tessera-auditability`; `bundle/mutations.py` (deterministic
   mutation generators, D9 classes); `docs/AUDITABILITY.md` with the
   CI-pinned generated block (byte-pin test, the BENCHMARK.md pattern);
   the CI matrix job (D9; bundle test subset only). Floors pinned in
   tests: equality 100%, detection 100%.

### Milestone 22 — the public proof (tag `milestone-22`)

*What becomes true:* a stranger can download two bundles — one honest,
one a cryptographically perfect fake — and separate them with one
offline command; the compliance mapping and the write-up exist; every
public sentence traces to the fixed claim above.

7. **0138 — transparency anchoring (opt-in).** `bundle/transparency.py`
   (D8), `--anchor` on emit, `--check-anchor` on verify, sidecar format,
   fixture-tested offline; staged one-shot runbook; the recorded public
   run executes only on Q1 = yes.
8. **0139 — compliance mapping.** `docs/COMPLIANCE.md` per D11;
   cross-links from BUNDLE/AUDITABILITY/README; mkdocs nav; citations
   re-verified at write time.
9. **0140 — the forged-bundle challenge.** `scripts/forge_challenge_bundle.py`
   (deterministic, committed — the forgery is itself reproducible and
   auditable: hash-chain-valid, internally consistent, wrong on the
   evidence); `data/challenge/` honest + forged bundles (synthetic
   corpora only, D12); `docs/CHALLENGE.md` (what to try to break, what
   each failure would mean, foil-script contrast); README challenge
   section. The D10 RAGAS one-shot script lands here, staged; its
   recorded measurement executes only on Q2 = yes. **Adversarial
   review** (this unit is the public attack surface).
10. **0141 — the story, told exactly.** WRITEUP addendum (the
    re-execution boundary: what is new, what is envelope, what was
    measured); MARKET.md dated addendum (the 2026-07 receipt-system
    prior-art map with sources, re-verified); README positioning
    refresh built on the fixed claim; CHANGELOG roll; final empty-diff
    audit; tag `milestone-22`; STATUS wrap with the next kickoff
    prompt.

## Acceptance criteria (the act, not one unit)

- [ ] `tessera bundle` + `tessera verify` round-trip: 100% verdict
      equality with the live harness across all gold cases of all three
      committed batteries, from the bundle alone, in a subprocess.
- [ ] Flip-a-byte: every mutation class detected (100%), correct verdict
      class, broken claim/link named; pinned in CI.
- [ ] Verify path is stdlib-only (import-guard test, the
      `test_default_import_graph_has_no_hdbcli` pattern).
- [ ] Cross-platform matrix green on byte determinism.
- [ ] Six eval lines byte-identical to `milestone-19`; frozen-core
      empty-diff audit clean at each milestone close.
- [ ] Every public sentence derivable from the fixed claim + caveats.
- [ ] Challenge reproducible from a clean clone by a stranger.

## Eval impact

The existing six lines: none (additive consumers only). New pinned
lines: the two Auditability floors (0137). If any existing metric moves,
the gate fails and the change is wrong by definition.

## Autonomy

Everything above is decided; units execute without interactive stops per
CLAUDE.md "Autonomous phase execution." Exactly three questions are the
maintainer's (none blocks M20/M21; defaults apply until answered):

- **Q1 — Rekor anchoring, recorded run:** posting demo-bundle roots to
  the public Sigstore log is an external, public act. Default: client
  ships fixture-tested + staged runbook; no public post.
- **Q2 — LLM-judge one-shot:** small API spend + a pinned judge config.
  Default: script staged + fixture-tested; no recorded measurement.
- **Q3 — technical-report staging:** whether unit 0141 additionally
  stages an arXiv-ready technical report (publication is the
  maintainer's act, under his identity). Default: WRITEUP addendum only.

## Risks

- **Closure/commitment design is the differentiator's hinge** (D3/D4):
  if verify ever grants `RE-DERIVED` to a claim whose closure isn't
  packaged, the headline claim silently collapses — this is why the
  taxonomy lands in unit 0133/0134, not later, and why 0134/0136/0140
  carry adversarial review.
- **Byte determinism on strangers' machines:** mitigated by D5 (proven
  canonical-bytes pattern, strings + Decimal data model) and guarded by
  the matrix; Windows line-ending and filesystem-ordering effects are
  explicitly in the 0137 test scope.
- **Version drift:** a bundle verified under engine vX may not
  re-derive under vX+1 — D6 makes this visible (`NOT-EVALUABLE`) instead
  of wrong; release notes must call out shape-set changes.
- **gha snapshot size:** the github_actions corpus is the largest; 0133
  measures bundle sizes and records them in BUNDLE.md — if impractical,
  the honest fallback is domain-scoped v1 (business + devex) with the
  gha limit documented, not a silent closure cut.
- **Scope discipline:** the moment any unit wants a new verification
  surface for arbitrary text, it has left this plan (see ROADMAP3 "will
  not do") — that is LLM-judge territory by another name.
