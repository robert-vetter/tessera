# 0139. `tessera bundle audit` — the decision record a buyer actually needs

- **Phase / milestone:** ROADMAP3 Milestone 22 (the public proof), the
  compliance-mapping unit — elevated from a doc to a real command.
  Trust-bearing (it makes regulatory-adjacent statements) → careful
  honesty review before merge.
- **Issue:** —
- **Status:** approved (autonomous session, per spec 0131 D11).

## Problem

Stars, upvotes, and virality are the wrong optimization for trust/audit
infrastructure — its value is realized when a serious buyer can adopt it
in a regulated, production workflow. This unit builds what that buyer
actually needs: from any trust bundle, a **decision record** that maps
the bundle's contents to the record-keeping and human-oversight *concepts*
named in the EU AI Act (Article 12 and Article 14), plus a plain auditor
summary — a deliverable that is invisible to a crowd and essential to a
compliance/engineering buyer. It is the concrete embodiment of "depth over
publicity."

## The honesty guardrail (load-bearing — this is the whole risk)

This is the project's highest overclaim risk, so the rules are strict and
enforced in the output text itself, not just the docs:

1. **Never "compliant", "certified", "regulator-ready", or "meets the
   standard."** The record *maps to the concepts named in* an article; it
   is a documentation aid, not an attestation or legal advice. Every
   rendered record and the doc carry that disclaimer verbatim.
2. **Get the dates right (they moved).** Per [MARKET.md §3](../docs/MARKET.md)
   (verified 2026-07-02): the Digital Omnibus **deferred** the Annex III
   high-risk obligations — Art. 12 logging, Art. 14 human oversight — to
   **Dec 2, 2027**; only Art. 50 transparency bites Aug 2, 2026. No
   deadline-panic framing. The record states the *deferred* timeline
   accurately and frames the mapping as "audit-ready by design," a
   tailwind, not an imminent cliff.
3. **The record faithfully reflects the verification verdict.** `audit`
   runs `verify_bundle` first. A bundle whose envelope is broken (exit 4)
   cannot be audited → refuse with the reason. Otherwise the record leads
   with the real verdict: a **FAILED** re-verification produces a record
   that says the decision's claims do **not** re-derive — the audit tool
   is never a rubber stamp (pinned: `audit` on the forged challenge
   bundle records FAILED).
4. **Scope stays the fixed claim.** The mapping is about *offline
   re-execution of claim-vs-evidence faithfulness and approval-gated
   action*, not truth in the world; the honest-limits of BUNDLE.md apply
   and are linked.

## Decisions

1. **New module `tessera/bundle/audit.py`**: `audit_record(bundle) ->
   AuditRecord` (frozen dataclass with `to_dict()`), pure/offline, a
   consumer of `verify_bundle` + the bundle fields. `render_text`.
2. **CLI: `tessera bundle audit <file> [--json]`** — a sibling verb (the
   spec-0117 dispatch, like `explain`/`keygen`). Exit 0 on a produced
   record, 4 if the envelope is broken (cannot audit), matching the
   verify envelope semantics.
3. **The mapping is grounded in real bundle fields**, not hand-waved:
   record-keeping/traceability ↔ the packaged question + claims + cited
   evidence + the re-derivable verdict; reconstructing *why* ↔
   re-execution (an auditor re-derives, not just reads); human oversight
   ↔ the action receipt's `requires_approval`/`approved` + drafted-not-
   sent; accountability of automated action ↔ the wire request → approval
   → claims → evidence chain. Each row: "concept named in Art. X" ↔ "what
   this bundle carries," with the disclaimer.
4. **`docs/COMPLIANCE.md`** (the plan's filename, spec 0131 D11): frames
   the feature, the mapping table, the corrected timeline, the "runtime
   evidence is bought by engineering, not deadline panic" position
   (MARKET §3), and the disclaimer. mkdocs nav + a README line.
5. **No network, no spend, no external claim.** Additive; frozen core
   untouched; six eval lines byte-identical.

## Scope

**In:** `bundle/audit.py`, the `audit` CLI verb, `docs/COMPLIANCE.md`,
README pointer, mkdocs nav, `tests/test_bundle_audit.py`.
**Out:** Rekor (0138), the write-up (0141); any "compliant" claim; any
legal advice; any non-mapping regulatory assertion.

## Acceptance criteria

- [ ] `tessera bundle audit data/challenge/honest.tsb` produces a record
      leading with verdict PASS and the Art. 12/14 mapping.
- [ ] `audit data/challenge/forged.tsb` produces a record that leads with
      **FAILED** and states the claims do not re-derive (never a stamp).
- [ ] A broken-envelope bundle → exit 4, "cannot audit", named.
- [ ] The rendered record contains the disclaimer (not compliant/legal
      advice; standards are drafts) and the **Dec 2, 2027** deferred date
      — pinned by a test so a stale/overclaiming edit fails the build.
- [ ] `--json` round-trips; stdlib-only (leak-guard extended).
- [ ] Gate green; six eval lines byte-identical.

## Eval impact

None — additive command + doc + tests.

## Risks / notes

- **Overclaim is the only real risk.** Mitigated by decision-2/3 tests
  (the disclaimer string and the deferred date are asserted; the forged
  bundle must record FAILED). If the regulation shifts again, this is a
  one-file text update — the code maps to concepts, not to a frozen date.
- The command name is `audit` (an audit/decision *record*), deliberately
  not `comply`, to avoid implying a compliance guarantee in the verb.
