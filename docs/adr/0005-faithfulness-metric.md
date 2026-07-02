# 0005. Faithfulness as a deterministic, provably-failable metric

- **Status:** accepted
- **Date:** 2026-06-09

## Context

"Trust is measured" is non-negotiable, and the brief warns that evaluation can
become theater. There is no LLM in this slice (ADR 0003), so faithfulness is
judged **structurally**, deterministically. The hazard: because the engine builds
every claim *from* its evidence, a naive structural check reads 1.0 almost by
construction — a tautology that proves nothing.

## Decision

**Faithfulness** = the fraction of emitted claims whose content is
**deterministically supported by their cited evidence**, where "supported" is
checked per claim shape: a surfaced snippet/clause appears in a cited record; an
aggregate recomputes exactly from its cited rows; a count matches the cited
records; a refuse-to-sum claim's cited rows actually span the named currencies.

**The definition includes its own falsifiability proof:** the check is *provably
able to fail*, demonstrated by a test that injects a known-unfaithful claim
(content not supported by its citation) and asserts the metric catches it (score
< 1.0). A reported 1.0 is therefore **earned, not tautological**. Faithfulness
carries a **hard floor of 1.0** — below it, `tessera-eval` exits non-zero (a build
failure).

**Coverage** (expected supporting evidence actually surfaced) and **quality** (gold
answers correct / refusals refused) are **reported, not gated**; coverage is
expected to sit **< 1.0** (e.g. the documented Lumière mention miss — currently
0.929) as an honest, improvable signal. The gold set is small, hand-curated,
committed, and documented, so every number is auditable.

## Consequences

- A strong **regression guard** and a real **provenance proof** — no claim can
  assert what its citations do not support, and the metric is demonstrably able to
  fail.
- It **forces claims to cite what they assert**: writing the verifier caught the
  composition identity claim under-citing its address count, fixed in this unit
  (the claim now cites the address records it describes).
- **Honest about its limits:** a structural check is **not** the semantic
  faithfulness a model judge would assess; a 1.0 means "every claim is mechanically
  supported by its evidence," not "the answer is wise." Coverage/quality < 1.0 are
  the honest part of the picture.

## Future work

LLM-judged semantic faithfulness; synthetic gold-data generation; trend/regression
history over time (all Phase 2+), with the same measured revisit trigger as ADR
0003.

## Alternatives considered

- **LLM-as-judge now.** Rejected: non-deterministic and against ADR 0003; the
  slice has no model.
- **Structural check without the adversarial proof.** Rejected: a tautological 1.0
  is exactly the "eval theater" the brief warns against.
- **Gate all three metrics with floors.** Rejected: coverage/quality floors are
  arbitrary at this baseline and would block honest, incremental work; faithfulness
  is the only invariant that must always hold.

## Addendum (2026-07-02, spec 0110 — audit B6/B7): blind spots named; refuse-kind claims now scored

The 2026-07-02 audit re-examined what the structural verifier does and does not
measure. Three findings, two of them *named* here as standing blind spots (with
committed specimens in `tests/test_trigger_specimens.py`), one *fixed* as a
transparent accounting change:

- **Over-citation is unpenalized (B6a, named).** The generic containment grammar
  accepts a claim if **any** cited record supports it, so decorative extra citations
  pass — a claim can launder an irrelevant record into its provenance trail. The
  shape-specific grammars are stricter (an aggregate must recompute from exactly the
  cited rows). Penalizing over-citation (e.g. an "every citation used" strictness
  metric, reported not gated) is recorded future work; changing the gated metric
  silently would violate the transparency rule.
- **Containment matches across word boundaries (B6b, named).** `normalize()` strips
  spaces/punctuation before substring matching — the same folding that absorbs
  umlaut/punctuation variance can match `"run 42 failed"` inside
  `"rerun 42 failed…"`. Inherent to the normalization's purpose; a specimen pins it.
- **Refuse-kind claims are now faithfulness-scored (B7, fixed).** The harness
  previously skipped faithfulness accounting entirely for refuse-kind cases, so a
  wrongly-answering engine's claims — or a partial answer's claims carried alongside
  a refusal (the mixed-currency case) — escaped the verifier. `_score` now runs the
  same per-claim check for every case kind. **Measured effect on every battery:
  zero** — all six lines byte-identical (correct refusals emit either no claims or
  claims that verify; the change widens what is *counted*, not what passes) — while
  the previously-unreachable failure mode (an unfaithful claim on a refuse case) can
  now fail the floor.
