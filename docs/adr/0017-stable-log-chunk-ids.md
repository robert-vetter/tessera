# 0017. Finer log chunking with stable, role-tagged chunk ids

- **Status:** accepted
- **Date:** 2026-06-27

## Context

Real GitHub Actions runner logs ingest as `log-span` chunks via
`sources/github_actions.py::parse_log_chunks`, which grouped lines by consecutive
`(job, step)`. A runner log is one long `(deploy, UNKNOWN STEP)` stream, so the
whole 60-line Pages-deploy log became **one** chunk, with the actual failure
(`##[error]HttpError: Not Found`, `status: 404`, `Ensure GitHub Pages has been
enabled`) at lines 50–57, behind ~49 lines of provisioning boilerplate.

Milestone 6 named this **long-document dilution** (`docs/STATUS.md`, spec 0058):
both BM25 length-normalization and the embedding's whole-document averaging let
the concise run-status row out-rank the long error chunk, so the synonymy answer
surfaced the failed *run*, not the *404 line*. Spec 0058 corrected gold-05 to
expect the run row as the honest compromise and named finer chunking as the fix.

Two things had to be decided together: **how** to split, and **how to id** the
result — because chunk ids were **positional** (`{run_id}.failed:chunk{index}`)
and committed gold cases pin them (gold-02 cites two `:chunk1` ids), so any
re-chunking silently renames records and breaks coverage matching.

## Decision

**Split each `(job, step)` group at its error marker.** When a group contains
`##[error]`, isolate the error cluster — the first marker (minus a small leading
context window) through the end of the group — into its own chunk. The preamble
becomes a separate chunk; a group with no error stays a single chunk. So the
Pages log becomes a boilerplate `chunk1` (lines 1–46) plus a focused `error1`
(lines 47–60, 14 lines) that the retriever — lexical or semantic — can surface
sharply instead of the diluted whole.

**Keep a small diagnostic-context window** (`_ERROR_CONTEXT_LINES = 3`, a
documented tunable knob) ahead of the marker, so the diagnostic printed
immediately above the exit — e.g. a formatter's `Would reformat:` lines just
before `##[error]Process completed with exit code 1` — is not severed from the
error it explains. Without it, RCA over the ruff log would lose `Would reformat`.

**Make chunk ids stable and role-tagged, not positional.** A chunk's id suffix is
its **role + ordinal**: `chunk{n}` for an ordinary/preamble span, `error{n}` for
an isolated error cluster. The error cluster of a run is always `error1`,
regardless of how many preamble lines precede it — so re-chunking the *context*
never renames the span a gold case cites. Gold cases now cite the failure by
`error1` (re-pointed from the old `chunk1`).

**RCA needs no change.** `explain_failure` already cites every `##[error]`-bearing
chunk and sorts chunks by id; with the split, only `error1` carries the marker,
so RCA cites it (and `chunk1`, the preamble, is correctly ignored). The recurrence
signature and cross-run matching key on the error chunks of each run, unchanged.

## Consequences

- **Easier:** the specific failure line surfaces, not just the run-status row —
  the de-dilution Milestone 6 deferred. The synonymy answer can now state the real
  cause (the 404 / "Pages not enabled" lines), and gold-05 can legitimately expect
  the error chunk on the semantic path (spec 0065).
- **Easier:** gold ids survive future re-chunking — the id contract is content/
  role-derived, so adjusting the context window or preamble splitting does not
  churn the gold set again.
- **Accepted cost:** each error-bearing log now yields two chunks (preamble +
  error), so `structural_edges` emits one extra `log_of` edge per such log, and
  the eval index carries the (boilerplate) preamble chunk. Harmless: RCA ignores
  non-error chunks, and the preamble is real evidence kept verbatim, not dropped.
- **Accepted cost — the context window is a heuristic.** Three lines is tuned to
  keep a formatter's diagnostic attached; a pathological log could place the
  diagnostic further above. Documented and tunable, like the resolution threshold.
- **Offline numbers are preserved.** gold-01/02 re-pointed to `error1` (still
  RCA-cited) keep their 1.0; gold-05 stays the offline lexical miss (zero token
  overlap is unaffected by chunking). The github_actions battery reads
  byte-identically offline (coverage 0.833, quality 0.800, faithfulness 1.0).

## Alternatives considered

- **Keep positional `chunk{index}` ids and re-point gold cases each time.**
  Rejected: re-chunking would silently rename records and re-break the gold set;
  a role-derived id is the stable contract the milestone needs.
- **Emit the error cluster as an *additional* overlapping chunk, keeping the full
  group chunk.** Rejected: overlapping chunks make RCA cite the failure twice
  (both the full chunk and the error sub-chunk carry `##[error]`) and double the
  recurrence matches — noise the non-overlapping split avoids.
- **A length threshold (only split logs over N lines).** Rejected as more
  arbitrary than the error-marker split: the marker is the real boundary, and the
  context window already prevents over-splitting a short log's diagnostic.
- **Drop the boilerplate preamble entirely.** Rejected: it is real evidence (what
  the runner attempted before failing); the project keeps log lines verbatim
  (ADR 0014). It is simply not an *error* chunk, so RCA ignores it.
