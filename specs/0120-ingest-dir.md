# 0120. `tessera ingest <dir>` — CSV + Markdown on your own data

- **Phase / milestone:** Milestone 18 Unit 4 (spec 0117 decision 8). The second
  BYO door: point Tessera at a local directory of CSV + Markdown described by a
  small declared config, and answer with the same claim-level provenance and
  honest refusals as every committed vertical. Carries **ADR 0029** (the config
  format). Trust-bearing → pre-merge adversarial review.
- **Issue:** —
- **Status:** approved (autonomous mode).

## Problem

`tessera connect github` (spec 0118) proves grounding on a foreign repo, but a
design partner's data is usually tabular + documents, not CI runs. Unit 4
generalizes what `sources/salt.py` + `sources/documents.py` do — read rows and
chunk text through the one door, resolve entities with multi-field ER, link
document mentions — into a **declared** mapping so the schema knowledge comes
from the user, not from code, with the engine untouched.

**Recorded decisions:**

1. **Config = `tessera.toml`, parsed with stdlib `tomllib`** (ADR 0029). No
   dependency; human-authored; validated with clear errors.
2. **Reuse the primitives unchanged:** `read_csv_rows`/`Locator.table_row` for
   tables, `chunk_text`/`Locator.doc_span` for documents,
   `resolve_entities(match_fields=…)` + `link_document_mentions` for the graph.
   New code lives in `tessera/ingest/` (a vertical-neutral answer layer *on*
   the engine, like `tessera/business/`), never in the engine.
3. **Row text is a `str.format` template over the row** — a faithful rendering
   of the row's own values (provenance requires the claim text be the row, not
   a computed value); a missing column is a named error.
4. **The answer path** (`tessera/ingest/answer.py`): lexical retrieval by
   default (provenance-carrying, refuse-on-zero-overlap — the engine's
   `answer`), plus **entity lookup** when the question names a declared
   display-name: gather the resolved entity's own records + its edge-connected
   records as verbatim cited claims — and **refuse when the name is ambiguous**
   (matches more than one distinct resolved entity). This is the concrete
   "ambiguous names refuse" contract and the exercise of the M9/M10 ER
   mechanism on foreign data.
5. **`ask`/`ingest` dispatch:** `tessera ingest <dir>` validates + ingests +
   reports (record counts, ER merges, ambiguous display-names, doc mentions);
   `tessera ask <dir> "…"` answers (a target that is a local directory with a
   `tessera.toml` routes to the dir corpus; otherwise it is a connect
   workspace — unambiguous, since `owner/repo` is not a local dir).
6. **Proof corpus, committed** (spec 0117 decision 2 covers *foreign snapshots*;
   this is a **small, public-domain, self-assembled** corpus, MIT-compatible
   like the synthetic data, so it is committed for clone-and-run
   reproducibility). `data/ingest_demo/`: SPDX open-source **license** facts
   (public/factual) as `licenses.csv` + `stewards.csv` (FK edge) + `notes.md`,
   with a deliberate **ambiguous name** ("BSD License" → BSD-2-Clause vs
   BSD-3-Clause, split by a `clauses` match field) to demonstrate the refusal.
   Origin recorded in the corpus `NOTICE`.

## Acceptance criteria

- [ ] `uv run tessera ingest data/ingest_demo` reports the ingested records
      (tables + document chunks), the ER outcome (merges + any ambiguous
      display-names), and exits 0.
- [ ] `uv run tessera ask data/ingest_demo "<question>"`:
      - a lexical question → grounded claims with provenance, or an honest
        refusal on zero overlap;
      - an unambiguous entity name → that entity's cited facts (rows +
        edge-connected rows), every claim with provenance;
      - an **ambiguous** entity name ("BSD License") → a refusal that names the
        ambiguity ("2 distinct entities …"), never a fabricated merged answer.
- [ ] Multi-field ER runs from declared `match_fields`: the two "BSD License"
      rows stay **distinct** components (a test pins it); a unique name is its
      own entity.
- [ ] Document mentions link `notes.md` chunks to the licenses they name (the
      cross-source link), pinned by a test.
- [ ] A malformed/missing config is a clean `IngestConfigError`, not a
      traceback (bad TOML, missing `id` column, unknown table in an edge,
      missing file).
- [ ] Gate green; six committed battery lines byte-identical; engine +
      `sources/` diff clean; `mkdocs build --strict` (ADR 0029 in nav/index).
- [ ] **Pre-merge adversarial review** (trust-bearing: foreign CSV/Markdown +
      a template render into claims; a config is parsed) — findings fixed or
      accepted in the PR.

## Scope

**In:** `tessera/ingest/` (config, source, answer, cli wiring),
`data/ingest_demo/`, tests, ADR 0029, README pointer, mkdocs nav. **Out:** any
engine/verifier/`sources/` change; a query language; computed/aggregated
claims (provenance = verbatim row/chunk text); non-CSV structured formats
(Parquet/SQL); the PILOT runbook (Unit 5).

## Eval impact

None on the committed lines (proven at the gate). The dir corpus is answered by
the engine's retrieval + a vertical-neutral entity lookup; no new gated metric.

## Live proof (recorded at implementation, 2026-07-03)

`uv run tessera ingest data/ingest_demo` (committed corpus): 9 table rows
across 2 tables + 3 document chunks; entity resolution → 12 resolved entities,
0 spurious merges, 4 document mentions; **ambiguous name reported: 'Portland'
→ 2 distinct entities**.

- `ask … "Tell me about Portland"` → **refused**: *"'Portland' is ambiguous —
  it names 2 distinct entities in this data (kept apart by entity resolution)."*
  The two Portlands (Oregon / Maine) stay distinct components because the
  declared `state` match field disagrees — the M9/M10 mechanism on foreign
  data.
- `ask … "What do you know about Santa Fe?"` → entity route: the city row
  (cities.csv), its region (regions.csv, via the FK edge), and the note
  (notes.md, via document mention) — three cited claims, all verifier-passed.
- `ask … "Which city is the oldest state capital?"` → lexical route: the
  Santa Fe note, grounded and cited.
- `ask … "quantum chromodynamics lattice gauge"` → honest refusal (zero
  overlap).

Reproduce with the two commands above (the corpus is committed and
public-domain, so this runs clone-and-run offline).

## Risks / open questions

- **Foreign CSV/Markdown is attacker-shaped:** the row template and chunk text
  flow into claims. Mitigated — claims are verbatim renderings the verifier
  checks by containment, and the UI (which renders untrusted HTML) is out of
  scope (it serves committed demo data only). The adversarial review covers
  template injection, config abuse, and provenance truthfulness.
- **Template surface:** `str.format` over a row dict — a crafted column name or
  `{}`-bearing cell must not break rendering or provenance; the review checks
  this (format-field abuse, missing keys).
- **Ambiguity detection quality:** name matching is normalized-equality against
  declared display-names; a name that is a substring of the question routes to
  entity lookup. Over-matching falls back to lexical; the refusal is the
  safe default.
- **The refusal fires only when a match field DISAGREES** (adversarial review,
  finding 6). Two genuinely-distinct entities that share a name *and* every
  declared `match_field` value will silently merge into one entity — this is
  inherent to entity-resolution-as-corroboration (ADR 0019/0020): the system
  splits same-named entities only when it has a *distinguishing* signal. So the
  contract is "a name whose declared distinguishing fields differ is refused as
  ambiguous," not a blanket "same name ⇒ ask which one." Choosing `match_fields`
  that actually distinguish the entities is the user's job; the demo's `state`
  field is exactly such a field for the two Portlands.
- **Foreign files, not remote fetch.** `ingest` reads the user's own local
  files; control sequences in a CSV cell / Markdown line are neutralized in the
  rendered claim (the connect door's decision, ADR 0028), but the files
  themselves are trusted-as-chosen. Paths are confined to the corpus dir; a
  duplicate id or table name is a refused config error.
