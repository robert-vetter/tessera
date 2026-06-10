# 0006. Deterministic question understanding; LLM deferred with explicit triggers

- **Status:** accepted (2026-06-10)
- **Phase:** 2

## Context

Phase 2 adds question routing and multi-step reasoning — the layers where most
systems first reach for an LLM. Tessera's engine so far is fully deterministic
(ADR 0003 lexical retrieval, ADR 0004 deterministic ER, ADR 0005 structural
faithfulness), which is what makes its trust numbers auditable and its CI
reproducible with no keys, network, or nondeterminism.

## Decision

Phase 2's routing (spec 0020) and multi-step reasoning (spec 0019) are
**rule-based and deterministic**: keyword/shape classification for routing,
name-containment entity finding, and arithmetic recomposition over graph
attributes for reasoning. **No LLM enters the engine in Phase 2.**

The LLM's place in Tessera remains what the project brief states: fluency and
orchestration *on top of* a grounded substrate — planned with the SAP
Generative AI Hub integration (Phase 4), and only where the deterministic layer
demonstrably falls short.

## Consequences

- Clone-and-run stays true; the eval gate stays meaningfully reproducible.
- The engine cannot understand free-form phrasings beyond its rules — an
  honest, documented limit surfaced as principled refusals, not guesses.

## Revisit triggers (deliberate, measurable)

1. **Routing/quality misses in the eval**: gold or synthetic cases show the
   rule router misdirecting questions or reasoning failing on phrasings users
   actually need (quality metric drops or cases must be contorted to pass).
2. **Phase 4 conversational surface**: a Joule-style interface needs NL
   fluency; the LLM then *narrates* grounded results (claims stay verifier-
   checked) rather than generating facts.
3. **LLM-judged faithfulness** (ADR 0005's own trigger) arrives — the judge and
   the engine LLM are separate concerns; either can arrive without the other.

## Alternatives considered

- **LLM router/reasoner now** — rejected: breaks reproducible CI and the
  no-keys local mode for a capability the current question shapes don't need.
- **Small local model (e.g. embedding classifier)** — rejected for the same
  reproducibility cost with less benefit than ADR 0003's embedding trigger,
  which already covers the retrieval side.
