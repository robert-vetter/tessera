"""BYO-data doors (Milestone 18): connect a foreign GitHub repo, ask offline.

The package behind ``tessera connect github <owner>/<repo>`` and
``tessera ask <owner>/<repo> "…"`` (spec 0118, ADR 0028): a bounded,
scrubbed, dev-time fetch into a gitignored local workspace, and an answer
path that reads only that workspace — through the same ingestion door,
graph machinery, RCA, and provenance contract the committed corpora use.
Nothing here is imported by the engine, the batteries, or the UI.
"""
