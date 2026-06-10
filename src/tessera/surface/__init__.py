"""The Joule-style conversational surface: one assistant, visible trust.

`uv run tessera-chat` (spec 0040) is the polished door over **both**
verticals: an interactive session with explainable routing, numbered claims,
explorable provenance (``:show N`` walks a claim back to its records,
locators, and resolution assertions), a live trust signal (every answer is
re-checked by the same verifier the eval uses), and — only when a provider
is configured (spec 0039) — an LLM narration of the verified claims under
the strict ADR 0013 boundary: rephrase, never add.

Like ``tessera.eval.registry``, this package is *wiring*: it may name both
verticals; the engine stays vertical-neutral.
"""
