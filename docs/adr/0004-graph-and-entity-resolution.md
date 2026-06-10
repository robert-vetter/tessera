# 0004. In-process knowledge graph with a non-destructive entity-resolution layer

- **Status:** accepted
- **Date:** 2026-06-09

## Context

Unit 4 must unify the two ingested sources into one queryable graph and resolve
when records across them refer to the same real-world entity (CAPABILITIES
Pillar 2). Entity resolution is fallible, so Pillar 2 also demands every merge be
*inspectable and reversible* — "entity resolution is treated as fallible and
auditable, not as ground truth." We must choose a graph substrate, a merge
representation, and a matching method, for a thin slice that stays clone-and-run,
deterministic, and offline (CLAUDE.md), and consistent with the lexical-first /
no-ML stance of ADR 0003.

## Decision

**Graph substrate — embedded / in-process.** The graph is a plain in-process
object model (nodes wrapping ingested records, structural edges, additive
assertions). No external graph database. SALT-shaped foreign keys become
deterministic structural edges; every node and edge traces back to its source
record.

**Merge representation — a non-destructive layer over raw nodes.** Resolution
never collapses or rewrites source nodes. A `Resolution` is a separate, additive
assertion that two organization-name nodes refer to the same real entity,
carrying **(a) a reason** (the matched normalized forms and the similarity score)
and **(b) a confidence**. Resolved entities are the **connected components** of
these assertions — *derived, not stored* — so removing an assertion re-splits the
cluster and leaves all raw data intact. Document references are linked by additive
`Mention` assertions, never by editing records.

**Matching method — deterministic, explainable, name-only string matching.**
Names are umlaut-folded, casefolded, and reduced to alphanumerics; similarity is a
deterministic ratio (`difflib.SequenceMatcher`) over the normalized strings. Pairs
at/above a **named, documented, tunable threshold** —
`DEFAULT_RESOLUTION_THRESHOLD = 0.85` in `tessera.resolution`, not a buried
literal — get an assertion; pairs below stay separate. Document→entity links use
normalized containment of a known entity name within chunk text. No embeddings or
ML.

**Confidence is a proxy, stated honestly.** The `confidence` on an assertion is
the similarity score used directly as a confidence proxy — it is **not** a
calibrated probability, and should not be read as one.

## Consequences

- **Easier:** merges are auditable and reversible — you can list *why* two records
  were judged the same and withdraw it without data loss; the graph is honest
  about its own fallibility.
- **Easier:** deterministic and offline, so the eval rests on reproducible
  resolution; no infrastructure to stand up for the slice.
- **Accepted cost — precision/recall, stated honestly.** A single name-similarity
  threshold trades precision against recall. At 0.85 it merges the
  *Bayerische/Bayersche/Bayerische* typos and *Müller/Mueller*, and keeps *Müller
  Logistik* vs *Nordwind Logistik* (shared "Logistik GmbH") apart — but it is a
  blunt instrument and will mis-resolve names that differ more than their typos or
  collide on generic tokens. We report this; we do not claim perfection.
- **Accepted cost — transitive over-merge.** Because entities are connected
  components, a single spurious high-similarity assertion can transitively merge
  two otherwise-distinct clusters. A known tradeoff of clustering by transitive
  closure, bounded here by the conservative threshold.
- **Accepted cost — document-mention recall.** Normalized containment links only
  references whose form matches a known entity name; a reference that drops the
  legal form (e.g. "Lumière Énergie", absent from the master data) is **not**
  linked — a named, tested known miss, not a hidden one.
- **Accepted:** no answering. The graph and its links exist; composing a
  cross-source answer over them is Unit 5.

## Future work

- **Multi-field matching.** Name-only matching is a deliberate slice
  simplification; real master-data ER matches on multiple fields (name **and**
  address, etc.). Address nodes already exist in the graph (as the targets of
  `has_address` structural edges), so multi-field matching is an **additive
  extension — more signals into the same assertion layer — not a redesign**.
- **Persistence / SAP HANA Cloud** as the graph + vector substrate, with the
  in-process model kept as the portable local mode (`docs/SAP_ALIGNMENT.md`).
  Neo4j is an alternative considered but not pursued.
- **Embeddings / ML matching** (and learned NER for document mentions) once the
  coverage/ER metrics (Unit 6) show deterministic string matching missing real
  links — the same measured revisit trigger as ADR 0003.

## Alternatives considered

- **Destructive merge (collapse duplicates into one canonical node).** Rejected:
  it discards which source said what and cannot be undone — the opposite of
  Pillar 2's "inspectable and reversible."
- **Neo4j / SAP HANA graph now.** Rejected for the slice: external infrastructure
  breaks clone-and-run and offline determinism before any measured need; HANA is
  the documented production target, not a slice dependency.
- **Embeddings / ML resolution now.** Rejected: premature and non-deterministic
  before the metric can justify it (consistent with ADR 0003).
- **Cluster-level assertions (store the merged set) instead of pairwise.**
  Rejected: pairwise links carry a per-pair reason + confidence and make
  reversibility granular; clusters are cleanly derived as connected components.

## Addendum (2026-06-10, spec 0036)

The "embeddings / ML matching" trigger **fired** with Phase 3's measured
devex coverage of 0.917 (`notif-svc`, similarity 0.429). Resolved
deterministically: **declared catalog aliases** asserted as ordinary
additive `Resolution`s (confidence 1.0, reason naming the declaration) —
see ADR 0010, which also records why embeddings stay deferred and what
would now justify them. The non-destructive assertion model needed no
change to express this; `checkout-svc` (0.846) is deliberately retained as
the named near-miss. The earlier addendum below (spec 0024) covers the
diacritic/legal-suffix refinements.

## Addendum (2026-06-10, spec 0024)

The coverage metric did what this ADR said it would: it identified the
Lumière document-mention miss, and the fix landed as two deterministic,
additive refinements — `normalize()` now folds non-German diacritics to base
letters (NFKD) instead of deleting them, and document-mention linking
tolerates a dropped legal suffix (reduced confidence 0.9, reason naming the
stripped form). Name-only matching, the 0.85 threshold, and the
non-destructive assertion model are unchanged; the proof tests (Bayerische
4-way merge, Müller ≠ Nordwind, reversibility) still hold. Gold coverage
moved 0.938 → 1.000 (`eval/history.jsonl`).
