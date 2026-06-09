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
