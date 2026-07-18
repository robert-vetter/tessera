# Audit records — mapping a decision to the EU AI Act

*Milestone 22 (spec 0139). `tessera bundle audit <file>` turns any trust
bundle into the record a compliance or engineering auditor actually needs.*

> **Not a compliance attestation.** This maps a bundle's contents to the
> *concepts named in* EU AI Act Article 12 (record-keeping) and Article 14
> (human oversight). It does not certify conformance with any standard, it
> is not legal advice, and the candidate technical standards
> (prEN 18229-1, ISO/IEC DIS 24970) are still drafts.

## The honest timeline (it moved)

Deadline-panic is the wrong frame, and it would be wrong on the facts. The
**Digital Omnibus** (political agreement mid-2026) deferred the Annex III
high-risk obligations — including **Art. 12 logging** and **Art. 14 human
oversight** — to **2 December 2027**. Only **Art. 50 transparency** applies
from 2 August 2026 ([MARKET.md §3](MARKET.md), re-verified 2026-07-02).

So this is not a cliff to panic-buy against. It is a *tailwind*:
audit-ready-by-design becomes more valuable toward the end of 2027, and in
the meantime the demand for runtime evidence is not driven by the
regulation at all — it is driven by engineering teams that cannot ship
agents they cannot trust ([MARKET.md §4](MARKET.md): Gartner projects >40%
of agentic-AI projects cancelled by 2027, inadequate risk controls a top
reason; quality is the #1 production blocker). **Runtime evidence
infrastructure is bought by engineering, not by a compliance deadline** —
which is the point.

## What the record maps

A trust bundle already carries everything an auditor needs; `audit` just
names the correspondence and leads with the verification verdict (a failed
re-verification produces a record that says so — never a rubber stamp).

| Concept the article names | What the bundle carries |
|---|---|
| **Record-keeping / traceability** (Art. 12) | the whole decision as one portable, tamper-evident file: the question, every claim, the exact evidence records each claim cites, and the verifier's verdict |
| **Reconstructing *why* an output was produced** (Art. 12 purpose) | re-execution — an auditor re-derives every claim's verdict *offline* from the packaged evidence, rather than trusting a log |
| **Human oversight** (Art. 14) | for an action bundle: the action is drafted, never auto-sent; the receipt records `requires_approval` and whether a human `approved` — the human-in-the-loop gate is *in* the record |
| **Accountability of an automated action** (Art. 14 purpose) | the receipt links the exact wire request → its approval → the verifier-passing claims → the evidence; nothing acts on ungrounded ground |

## Try it

```console
$ uv run tessera bundle audit data/challenge/honest.tsb
verdict:  PASS — the decision RE-VERIFIED: every claim re-derives from its evidence.
…
  [✓] Art. 12 · Record-keeping / traceability
  [✓] Art. 12 (purpose) · Reconstructing why an output was produced
  [—] Art. 14 · Human oversight   (answer-only bundle — an action bundle carries one)

$ uv run tessera bundle audit data/challenge/forged.tsb
verdict:  FAIL — the decision FAILED re-verification: its claims do NOT re-derive …
```

`--json` emits the structured record. A bundle whose envelope is broken
cannot be audited (exit 4) — you cannot produce an audit record from a file
you cannot even read intact.

## Scope

The record inherits the bundle's scope: it attests offline re-execution of
*claim-vs-evidence faithfulness* and *approval-gated action*, not truth in
the world (the [honest limits](BUNDLE.md#honest-limits) apply). It is a
faithful projection of what `tessera verify` computes, in the vocabulary an
auditor uses.
