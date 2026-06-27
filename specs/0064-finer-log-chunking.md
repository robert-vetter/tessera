# 0064. Finer log chunking: isolate the error cluster, stabilize chunk ids

- **Phase / milestone:** Milestone 7 — Unit 5 (of spec 0060)
- **Issue:** —
- **Status:** approved (autonomous mode; id contract recorded in **ADR 0017**)

## Problem

The real Pages-deploy log ingests as **one** 60-line `log-span` chunk
(`parse_log_chunks` groups by `(job, step)`, and the runner log is a single
stream), with the actual failure (`HttpError: Not Found`, `status: 404`, `Ensure
GitHub Pages has been enabled`) buried at lines 50–57 behind ~49 lines of
provisioning boilerplate. Milestone 6 named this **long-document dilution**: even
with embeddings, the concise run-status row out-ranks the diluted whole-log
chunk, so the synonymy answer surfaces the failed *run*, not the *404 line* (spec
0058 compromised gold-05 to expect the run row). This unit makes the failure its
own focused chunk so the specific line can surface — with a **stable chunk-id
contract** so committed gold ids survive the re-chunking.

## Acceptance criteria

- [ ] **Error-cluster isolation.** `parse_log_chunks` splits a `(job, step)` group
      carrying `##[error]` into a preamble chunk and an isolated error chunk (the
      marker, minus a small leading context window, through the group end). The
      Pages error chunk is short (≈14 lines, not 60) and carries the 404 cause;
      logs without an error marker stay a single chunk.
- [ ] **Diagnostic-context window.** A few lines ahead of the marker ride along
      (`_ERROR_CONTEXT_LINES = 3`, documented + tunable), so a formatter's
      `Would reformat:` lines stay attached to the `##[error]Process completed`
      exit — RCA over the ruff log still surfaces both.
- [ ] **Stable, role-tagged ids (ADR 0017).** Chunk id suffix is `chunk{n}`
      (preamble) / `error{n}` (error cluster), role-derived not positional, so
      re-chunking context never renames the failure span. Gold-01/02 re-pointed
      from `:chunk1` to `:error1`.
- [ ] **RCA unchanged + green.** `explain_failure` cites the `##[error]` chunk
      (now `error1`), recurrence keys on the error chunks of both Pages runs; the
      RCA tests pass with `error1` ids.
- [ ] **Offline numbers preserved.** The github_actions battery reads
      byte-identically offline (coverage 0.833, quality 0.800, faithfulness 1.0);
      gold-05 stays the offline lexical miss (zero token overlap is unaffected).
- [ ] **De-dilution demonstrated.** The stub-semantic battery test now shows the
      answer surfacing the isolated `error1` chunk and rendering the actual 404 /
      "Pages not enabled" lines — not just the run row.
- [ ] **Gate green** under the usual checks; `structural_edges` / chunk-count
      tests updated for the extra preamble chunk.

## Scope

**In:** `parse_log_chunks` (error isolation + role-tagged ids), the `_log_chunks`
/ `structural_edges` id construction, gold-01/02 re-pointing, the github_actions
source + battery tests, ADR 0017.

**Out:** gold-05's expected_support/facts re-point to the error chunk + the ER
ownership gold case (Unit 6, the eval-surface changes); the **online** run that
records the close (Unit 7); the synthetic devex logs (already finely chunked by
`chunk_text`'s blank-line split — unchanged).

## Eval impact

Offline numbers **unchanged** (gold-01/02 re-pointed keep 1.0; gold-05 stays the
recorded lexical miss). The de-dilution is a retrieval-quality improvement on the
**semantic** path, formalized as gold-05's recorded online close in Units 6–7.

## Risks / open questions

- **Chunk-id renumbering** (the sharp risk) is exactly what ADR 0017's stable
  role-tagged ids address; gold-01/02 are re-pointed in this unit, and no further
  re-chunking will churn them.
- **The context window is a heuristic** (3 lines, tuned to keep `Would reformat`
  attached). Documented and tunable; a pathological log could place the
  diagnostic further above — acceptable, recorded in ADR 0017.
- **An extra preamble chunk** enters the index/graph per error log. Harmless: RCA
  ignores non-error chunks; the preamble is real evidence kept verbatim.
