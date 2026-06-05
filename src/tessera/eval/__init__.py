"""The evaluation harness — Tessera's "trust is measured" plumbing.

This package is the scaffold: it can be *run* from day one (so the eval never
bitrots and `/verify` always has something to invoke), but it does not yet
*score* anything. With no gold cases it reports, honestly, "no gold set evaluated
yet" rather than a fabricated number. The metric definitions, the curated gold
set, and the faithfulness computation arrive in a later unit (see
``specs/0011-eval-harness-scaffold.md`` for the deferral, and the roadmap for
Unit 6). Keeping a runnable-but-honest harness now is the seed of the metric, not
the metric.
"""
