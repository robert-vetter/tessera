"""Source-specific ingesters.

Each module here knows one source's schema and turns it into the engine's common
representation. The engine (:mod:`tessera.ingestion`, :mod:`tessera.grounding`)
stays unaware of any of them — vertical/source specifics never leak into the
core, per ``CLAUDE.md``.
"""
