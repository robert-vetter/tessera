# 0008. The core/vertical boundary, and what Phase 3 may touch

- **Status:** accepted
- **Date:** 2026-06-10

## Context

Phase 3 adds the DevEx Copilot — the proof that the engine is general
(principle 5, ROADMAP Phase 3 milestone: "two genuinely different verticals
run on one unchanged core, both measured"). That proof is only as strong as
the definition of "core" and "unchanged", so both must be fixed **before**
any DevEx code exists, not argued afterwards.

Auditing the Phase 2 tree honestly: the modules are not all the same kind of
thing. `grounding`, `ingestion`, `graph`, `resolution`, `retrieval`, and the
eval *mechanics* are vertical-neutral. But `composition`, `reasoning`,
`conflicts`, and `routing` encode the **business vertical's question shapes**
(SALT kinds like `I_Customer`, the `sold_to` relation, renewal dates), and
`eval/metrics.py` shapes 2–5 encode the business **claim grammar** ("net
order value", customer/address counts). They live in the engine namespace,
but they are the business vertical's answer layer built *on* the core — a
boundary Phase 1–2 never needed to draw, and Phase 3 must.

Two things the core genuinely cannot express today (the ADR-worthy findings
the phase kickoff anticipated):

1. **Recurrence verification.** "This failure happened before" asserts that
   the same evidence fragment occurs in several distinct sources. No existing
   verifier shape can check a claim that spans citations this way; without a
   new shape, RCA's most valuable claim would be unverifiable (forbidden) or
   verified by DevEx-specific logic in eval internals (also forbidden).
2. **A second battery.** The harness is hardwired to one graph, one KB, one
   engine dispatch, and one synthetic generator. Measuring a second vertical
   *requires* touching eval internals (see ADR 0009).

## Decision

**The frozen core.** These files are byte-identical from tag `phase-2`
through tag `phase-3`: `grounding.py`, `ingestion.py`, `graph.py`,
`resolution.py`, `retrieval.py`, `routing.py`, `composition.py`,
`reasoning.py`, `conflicts.py`, `knowledge.py`, `cli.py`,
`sources/salt.py`, `sources/documents.py`, and `eval/synthetic.py`. The
phase-close audit records `git diff phase-2..phase-3` over them; it must be
empty.

**The vertical layer.** All DevEx logic lives in new files: `sources/devex.py`
(ingesters) and the `tessera/devex/` package (graph assembly, RCA,
change-summaries, routing, CLI, synthetic generator). Verticals may *call*
core primitives (`resolve_entities`, `link_document_mentions`, BM25
retrieval, `Locator(kind=...)` with new kinds) but never reach into or alter
them. The business layer stays where it is this phase — relocating it into a
symmetric `verticals/` namespace is deliberate Phase 4 polish, recorded here
so the asymmetry is a known state, not drift.

**Two sanctioned, vertical-neutral core deltas — and only these:**

1. `eval/metrics.py` gains **one generic claim shape**: a claim quoting
   fragment(s) and naming its sources is supported iff every quoted fragment
   appears (normalized) in **every** cited record, the named sources equal
   exactly the cited records' origins, and there are ≥ 2 citations. It
   contains zero vertical vocabulary and serves any vertical (recurring log
   signatures, a ticket id shared by a PR and a tracker row, a clause echoed
   across documents).
2. The eval harness/CLI/history are parameterized over **batteries**
   (ADR 0009). Scoring semantics do not change; the business battery must
   reproduce its Phase 2 numbers exactly.

**Convention clarified, not changed:** node kind `"document"` means *any
unstructured chunk node* (a contract clause, a log section, a diff hunk).
Core mention-linking applies to all of them unchanged; a vertical
distinguishes its document types by `origin.source`, which provenance already
carries.

## Consequences

- "Unchanged core" becomes a **checkable claim** (an empty diff), not an
  assertion — the strongest possible form of the Phase 3 milestone.
- Vertical question shapes are acknowledged as inherently per-vertical;
  generality is claimed for the substrate (ingestion → graph → resolution →
  retrieval → eval), which is what the milestone means.
- Accepted cost: business claim shapes 2–5 remain in `eval/metrics.py` for
  this phase — an acknowledged, recorded leak, scheduled for the Phase 4
  relocation rather than churned mid-proof.
- Accepted cost: namespace asymmetry (`tessera/devex/` vs business modules at
  top level) until Phase 4.
- Where the core still cannot express something, the rule stands: record the
  finding (spec/ADR), refuse honestly at runtime — never leak.

## Alternatives considered

- **Generalize `composition`/`reasoning` now** (parameterize kinds/relations
  so both verticals share one answer layer). Rejected: rewriting the core
  mid-proof destroys the "unchanged" evidence and risks regressions in the
  measured business behaviour for an abstraction with exactly two data
  points. Revisit when a third vertical (or Phase 4) shows the right shape.
- **No core deltas at all.** Rejected: recurrence claims would be either
  unverifiable (violates "no claim without checked support" — ADR 0005) or
  composed only of verbatim snippets (the answer could no longer *say* the
  thing that makes RCA useful); and the eval simply cannot measure a second
  vertical unparameterized — leaving DevEx unmeasured violates principle 3.
- **DevEx-specific shapes in `metrics.py`** (mirror how business shapes got
  there). Rejected: it deepens the recorded leak exactly when the phase
  exists to prove the opposite.
- **Plug-in verifier registry** (verticals register claim shapes). Rejected
  for now: more mechanism than two verticals justify, and a registry invites
  per-vertical "creative" shapes that erode the auditable, central metric
  definition (ADR 0005). The single generic shape covers the need.
