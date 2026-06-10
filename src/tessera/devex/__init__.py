"""The DevEx Copilot vertical (Phase 3).

Everything DevEx-specific lives in this package (ADR 0008): graph assembly
over the ingested corpus, the root-cause-analysis and change-summary answer
paths, routing, and the vertical's CLI door. It *calls* the core engine —
grounding, ingestion, graph, resolution, retrieval — and changes none of it;
that boundary is the point of the phase.
"""
