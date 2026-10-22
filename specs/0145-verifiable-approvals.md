# 0145. Verifiable approvals — the sign-off becomes a cryptographic artifact

- **Phase / milestone:** ROADMAP3 Milestone 22 — an added unit in the
  0142–0144 pattern. Trust-bearing (it renders approval verdicts) →
  honesty rules pinned in tests.
- **Issue:** —
- **Status:** approved (autonomous session; decision and rationale
  recorded here per CLAUDE.md "Autonomous phase execution").

## Problem

The project's positioning line is *"the agent can only say what it can
prove — and only do what you approve."* The first half is cryptographic;
the second half is, until this unit, a boolean flag: action receipts
record `requires_approval`/`approved`, but nothing proves **who**
approved **what**. In every enterprise approval workflow (SAP release
strategies, four-eyes sign-offs) the questions that matter are exactly
those two — and "what" must mean *the exact state that was approved*,
not "roughly that decision".

This unit makes an approval a **detached, signed artifact** bound to the
bundle's sealed root: `tessera bundle approve decision.tsb --key
manager.key` produces `decision.approval.json` — an Ed25519 signature
over a canonical payload containing the bundle's root. Change one digit
of the decision and re-seal: the root changes and the approval no longer
applies, verifiably, offline. `tessera verify decision.tsb --approval
decision.approval.json` reports each approval (valid / invalid, named);
trust policies gain `approvals` rules (`require: N`,
`allowed_approvers`, `distinct_approvers`) so four-eyes becomes one
policy line, enforced by the same fail-closed engine as everything else.

**Why this unit now (the audience test, recorded):** the maintainer
asked for a feature both an SAP-shaped enterprise audience and the
Z Fellows audience would rate highest. Candidates: policy-gated emission
(sanctioned by ADR 0034 as convenience — incremental), a decision-diff
tool (strong demo, kept as named future work), a local hash-linked
ledger (overlaps the reserved Rekor unit). Approvals win: they complete
the product's own tagline, they speak the enterprise's native
approval-workflow vocabulary with a property those workflows lack
(binding to exact bytes), and they compose with the whole stack —
receipts → chains → policies → **approvals** → audit records.

## Decisions

1. **Detached artifact, never a bundle section** (ADR 0035). The bundle
   section set is closed and byte-stable; an approval is a *third
   party's* post-seal act — embedding it would force a re-seal (changing
   the very root that was approved) and cap the approver count. A
   detached file composes: N approvers, added at any time, bundle bytes
   untouched. Same layering as policies: the bundle carries evidence;
   the surrounding artifacts carry judgment.
2. **The artifact:** `{"format": {"name": "tessera-approval", "major":
   1}, "approves_root": <root>, "note": str|null, "at": str|null,
   "approver": {"algorithm": "ed25519", "public_key": hex},
   "signature": hex}` — the signature is over the canonical bytes of the
   payload (`format`, `approves_root`, `note`, `at`). Creating one needs
   the `sign` extra (PyNaCl, the spec-0135 pattern); **checking one is
   pure stdlib** (the existing RFC 8032 verifier), so `tessera verify`
   stays dependency-free.
3. **Identity, not time — stated honestly.** An approval proves *who*
   approved *what*. The optional `at` field is the approver's **claim**,
   signed but not proven — proving *when* honestly requires a
   transparency log, which is exactly the reserved anchor/Rekor unit
   (0138). The docs say this plainly; no timestamp theater.
4. **Approvals inform; policies enforce.** `verify --approval a.json`
   (repeatable) checks each artifact — root match against the *actual*
   recomputed bundle root, signature verification — and reports it
   (`VerifyReport.approvals`, additive; rendered + in JSON). Invalid
   approvals never change the bundle's own verdict (they are attestations
   *over* it); consequences come from policy: new fail-closed rule group
   `approvals: {require: int, allowed_approvers: [hex], distinct_approvers:
   bool}` counting only **valid** approvals (and only allowed ones when
   the list is given). Verify run without `--approval` against a policy
   requiring approvals → violation ("0 valid approvals") — fail-closed
   presence semantics.
5. **CLI:** `tessera bundle approve <file> [--key K] [--note …] [--at …]
   [-o out]` (default out: `<file>.approval.json`; refuses to overwrite);
   `tessera verify <file> --approval <a.json> …`; front-door help.
6. **Docs:** `docs/APPROVAL.md` (exact-bytes binding, the four-eyes
   policy demo, the identity-not-time honesty note), POLICY.md rule
   table extended, README pointer, mkdocs nav, one clause in the
   SAP_ALIGNMENT governance addendum (release-strategy/four-eyes
   mapping — mapping language only).

## Scope

**In:** `bundle/approval.py`, `verify_bundle(approvals=…)` +
`VerifyReport.approvals`, policy `approvals` rules, CLI verb + flag,
`tests/test_bundle_approval.py`, docs as above.
**Out:** timestamp proofs (Rekor, 0138), approval revocation (named
future work), org key directories / role mapping (ADR 0032 scope),
embedding approvals in bundles (rejected), decision-diff (named future
work).

## Acceptance criteria

- [ ] `approve` → `verify --approval` reports a valid approval with the
      approver's key; JSON carries it.
- [ ] **Exact-bytes binding pinned:** an approval for the honest
      challenge bundle is INVALID against the forged one (root mismatch,
      named); a re-sealed tampered bundle invalidates prior approvals.
- [ ] A garbage signature, a wrong-format file, a malformed artifact →
      named outcomes (malformed file: CLI exit 4).
- [ ] Policy: `require: 2` with one valid approval → violated, named;
      `distinct_approvers` counts a duplicate key once;
      `allowed_approvers` excludes others; unknown approvals-rule key →
      fail-closed refusal.
- [ ] End-to-end four-eyes (needs `sign` extra, skip-marked like spec
      0135's tests): two keys, two approvals, policy → COMPLIANT exit 0;
      one approval removed → exit 5.
- [ ] The approval-check path is stdlib-only (leak-guard); creating
      approvals without the extra fails with the clean actionable error.
- [ ] Gate green; six eval lines byte-identical; frozen core + agent
      chain empty-diff; mkdocs strict green.

## Eval impact

None — additive module + CLI + policy rules + docs + tests.

## Risks / notes

- Wording discipline: an approval binds a **key**, not a human identity
  (key distribution out of scope, ADR 0032 — same honest limit as bundle
  signing, restated in APPROVAL.md).
- The `at` overclaim risk is handled by decision 3 (claim, not proof;
  pinned phrasing in the doc).
