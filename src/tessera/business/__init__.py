"""The Business Data Copilot vertical — the answer layer over the engine.

Relocated here from the package top level in Phase 4 (spec 0037), repairing
the namespace asymmetry ADR 0008 recorded: a vertical-neutral core
(`tessera.grounding`, `ingestion`, `graph`, `resolution`, `retrieval`, …)
with two sibling verticals beside it — `tessera.business` and
`tessera.devex` — each owning its question shapes, demo knowledge, routing,
CLI door, and synthetic eval generator, and each calling core primitives
without reaching into them.
"""
