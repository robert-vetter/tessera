# 0029. `tessera ingest <dir>` is driven by a declared TOML config

- **Status:** accepted
- **Date:** 2026-07-03

## Context

Milestone 18 Unit 4 (spec 0120) generalizes the ingestion door to *any* local
directory of CSV + Markdown, so a design partner can point Tessera at their own
files. The engine already ingests structured rows and text chunks through one
door (ADR 0002); what a generic directory lacks is the *schema knowledge* the
committed sources hard-code in Python (`sources/salt.py` knows which column is
the id, which is the name, which are the ER match fields). For foreign data
that knowledge must come from the user, not from code — which means a declared
configuration file. The question is what format it takes.

Constraints that bind the choice: the project is **stdlib-only, zero runtime
dependencies, clone-and-run** (a core claim verified every phase); the file is
**authored by a non-Tessera pilot user** by hand, so it must be readable and
commentable; and it must express, per row-table: the source file, the id
column, an optional display-name column (for entity resolution), optional
ordered `match_fields` (the M9/M10 multi-field ER mechanism, ADR 0019/0020), a
row-text template, node attributes, and optional foreign-key edges — plus a
list of document files.

## Decision

**The config is `tessera.toml` at the root of the ingested directory, parsed
with the standard library's `tomllib`.** TOML is in the Python 3.12 stdlib
(read-only `tomllib`), so it adds **no dependency** and keeps clone-and-run
intact; it is designed for hand-authored config, supports comments (a pilot
annotates their mapping), and expresses the table/document array-of-tables
structure directly. The loader validates required keys and raises a clear,
user-facing error naming the file and field on any problem — the config is
foreign input and is treated as such.

Shape (abbreviated):

```toml
name = "acme-catalog"
snapshot_date = "2026-07-03"          # optional; deterministic provenance

[[tables]]
name = "license"
file = "licenses.csv"
id = "spdx_id"                        # column → the natural key
display_name = "name"                 # optional → the entity name (for ER)
match_fields = ["clauses"]            # optional ordered corroborating attrs
attributes = ["clauses", "year"]      # columns attached as node attributes
text = "{name} ({spdx_id}): {year}, {clauses}-clause."   # row rendering
  [[tables.edges]]
  column = "steward_id"               # FK column → another table's id
  to = "steward"
  relation = "stewarded_by"

[[documents]]
file = "notes.md"                     # or glob = "*.md"
```

Ingestion reuses the existing primitives unchanged: `read_csv_rows` +
`Locator.table_row` for tables, `chunk_text` + `Locator.doc_span` for
documents, `resolve_entities(match_fields=…)` and `link_document_mentions` for
the graph. The generic answer path lives in `tessera/ingest/` (vertical-neutral
answer layer built *on* the engine, like `tessera/business/` — not in it):
lexical retrieval by default, and an **entity lookup** when the question names a
declared display-name — which **refuses when the name is ambiguous** (resolves
to more than one distinct entity), the concrete "ambiguous names refuse"
contract.

## Consequences

- **Easier:** a pilot maps their own CSV/Markdown with a readable file and zero
  install; the engine and its ingestion primitives are untouched (the M18
  frozen-core audit stays clean); the ER mechanism proven on synthetic SALT now
  runs on foreign data with only declared `match_fields`.
- **Accepted cost:** TOML `tomllib` is read-only (fine — we only read config)
  and has no schema validator in the stdlib, so validation is hand-rolled with
  explicit messages. A malformed config is a clean error, not a traceback.
- **Accepted cost:** the row-text template is Python `str.format` over the row
  dict — a missing column is a named error; this is a small templating surface,
  not a full expression language (deliberately — provenance requires the text
  stay a faithful rendering of the row, not a computed value).
- **Accepted cost:** the entity-lookup answer is a modest vertical-neutral
  addition in `tessera/ingest/`, not the rich per-vertical routing of business
  or DevEx; a generic directory has no known question shapes, so lexical
  retrieval + entity lookup + honest refusal is the principled floor.
- **Accepted cost / stated limit:** the ambiguity refusal fires only when a
  declared `match_field` *disagrees* between same-named rows (ER-as-
  corroboration, ADR 0019/0020). Two distinct entities sharing a name AND every
  match-field value merge silently — so the user must choose `match_fields`
  that actually distinguish their entities; the refusal is not a blanket
  same-name detector. Foreign row/document text is neutralized of terminal
  control sequences before it becomes a claim (ADR 0028's decision, applied
  here too); files are confined to the corpus directory; duplicate ids and
  duplicate/reserved table names are refused config errors.

## Alternatives considered

- **JSON config.** Also stdlib, but no comments and clumsier for a human to
  author by hand; TOML is the better fit for a hand-written mapping.
- **YAML config.** The most common config format, but **not stdlib** — it would
  add PyYAML, breaking the zero-dependency claim for a convenience.
- **Infer everything (no config).** Rejected: which column is the id, the name,
  or an ER match field is genuine schema knowledge a heuristic would guess
  wrong; a wrong id silently corrupts provenance. Declaring it is honest and
  puts the user in control.
- **A Python plugin per corpus** (like `sources/salt.py`). Rejected for the BYO
  path: it demands the user write and import code; a declarative file is the
  lower-friction, safer surface for a pilot.
