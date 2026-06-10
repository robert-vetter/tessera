# 0013. The narration boundary: an LLM may rephrase verified claims, never add to them

- **Status:** accepted
- **Date:** 2026-06-10

## Context

ADR 0006 deferred LLMs from the engine with explicit triggers; trigger 2 — "a
Joule-style interface needs NL fluency; the LLM then *narrates* grounded
results (claims stay verifier-checked) rather than generating facts" — fires
with the Phase 4 conversational surface (spec 0040). The platform seam
(ADR 0012) provides the model access (GenAI Hub, Anthropic fallback), off by
default. What needs deciding is the *boundary*: where exactly an LLM's text
may appear, and what mechanically prevents it from becoming a fact source.

## Decision

**Narration is presentation, never evidence.** The deterministic pipeline —
routing, retrieval/composition, refusal, claim-level provenance, live
verification — is unchanged and always rendered. Narration, when enabled, is
one additional paragraph **below** the canonical claims, visibly labelled as
LLM-phrased and explicitly not evidence.

**Three mechanical guarantees, in code, not policy:**

1. **Input restriction.** The narrator sees only the question and the already
   verifier-checked claim texts. It is invoked after verification, so there
   is no path by which narrated text reaches the verifier, a claim, or the
   eval.
2. **A deterministic novelty guard.** The narration is scanned for "fact-like
   tokens" — numbers/amounts and id-like tokens (`R-1042`, `DEVEX-187`,
   `SVC-NOTIF`, …). Any such token absent from the claims/question rejects
   the narration outright (an honest notice is printed instead). Guards are
   pure functions, unit-tested with fabricated-fact cases.
3. **Silent degradation.** No provider configured → no narration; provider
   error (`ProviderError`) → deterministic rendering, never a blocked or
   degraded answer. A refusal is never narrated — it is already one honest
   sentence.

**Stated limitation:** the guard is conservative, not complete — it catches
fabricated quantities and identifiers, not every possible semantic drift
(e.g. an unfounded "therefore"). That residual risk is why the boundary's
*primary* defence is placement: narration is additive text under canonical,
independently verified claims, and disabling it costs nothing.

## Consequences

- The Joule-style fluency arrives with zero change to the trust story: the
  eval, the floor, the claims, and the provenance are byte-identical with
  narration on or off.
- The same narrator serves both verticals (it works on claim texts, not
  vertical vocabulary) — no per-vertical narration code.
- Accepted cost: narration quality depends on the configured model and is
  unmeasured by the eval (deliberately — measuring prose quality is not the
  trust metric's job; ADR 0005's scope stands).

## Alternatives considered

- **LLM composes the answer, verifier checks afterwards.** Rejected: the
  verifier's grammars cover claims the deterministic engine *composes*; free
  LLM prose would need an LLM judge (ADR 0005's separate, still-untriggered
  concern) and would put generation upstream of trust.
- **Narration as a claim with citations.** Rejected: a paraphrase is not
  evidence and must not be citable; making it a `Claim` would launder model
  text into the provenance model.
- **Semantic entailment check on narration.** Rejected for now: needs a
  model to police a model, with its own failure modes; the deterministic
  token guard + placement covers the realistic failure (fabricated numbers
  and ids) without new dependencies.
- **Always-on narration with a local small model.** Rejected: breaks the
  no-keys/no-model clone-and-run guarantee for cosmetics.
