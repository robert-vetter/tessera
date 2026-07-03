"""BYO directory ingestion (Milestone 18, Unit 4): CSV + Markdown on your data.

The package behind ``tessera ingest <dir>`` and ``tessera ask <dir> "…"`` (spec
0120, ADR 0029): a declared ``tessera.toml`` maps a directory of CSV tables and
Markdown documents onto the engine's existing ingestion door — rows and text
chunks, multi-field entity resolution, document-mention linking — and a
vertical-neutral answer layer answers over it with claim-level provenance and
honest refusals (including "this name is ambiguous"). Nothing here changes the
engine, the sources module, or any battery.
"""
