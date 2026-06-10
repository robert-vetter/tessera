# 0027. DevEx ingestion through the same door

- **Phase / milestone:** Phase 3 — second vertical (DevEx Copilot), Unit 2
- **Issue:** —
- **Status:** approved (autonomous mode; decisions recorded here)

## Problem

The DevEx corpus must arrive in the engine the way the business corpus does:
through the `Ingester` contract, as `EvidenceRecord`s with mandatory origins
(Pillar 1: "structured and unstructured arrive through the *same* door").
This is the first half of the generalization proof — if log lines and diff
hunks need a different representation than rows and clauses, principle 5 has
already failed.

## Acceptance criteria

- [ ] `tessera/sources/devex.py` ingests all eight source shapes —
      components, owners, pipelines, runs, tickets, prs (structured) and
      pipeline logs + PR diffs (unstructured) — emitting `EvidenceRecord`s
      with natural-key ids and the manifest's snapshot date.
- [ ] Logs are chunked by the **engine's** `chunk_text` (the format's
      blank-line job sections meet the existing contract) with a `log-span`
      locator (lines + section + chunk); diffs are chunked **per hunk** with
      a `diff-hunk` locator (file + hunk + lines). Both locators are new
      `kind`s of the *unchanged* `Locator` type — constructed directly,
      cashing in ADR 0002's forward-compatibility a third time.
- [ ] **Zero core changes** (ADR 0008 frozen list untouched).
- [ ] Tests: Ingester conformance, id uniqueness/stability, snapshot-date
      provenance, signature-bearing chunk for R-1042 with the right section,
      PR-201's three hunks with file paths, every record's `source` renders.

## Scope

**In:** the source module + tests.
**Out:** graph assembly / name exposure / structural edges (Unit 3); any
answer path; any core-file change.

## Eval impact

None yet — the records exist but nothing consumes them until Unit 3+. The
business battery must stay at its recorded numbers (checked by `/verify`).

## Risks / open questions

- Diff hunk text includes its `diff --git` header line so each chunk is
  self-describing evidence; the locator carries file/hunk/lines. If hunk
  text proves too noisy for retrieval later, that is a retrieval finding to
  measure, not a reason to reshape records.
