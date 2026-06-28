# 0021. A Markdown heading leads its section, not a chunk of its own

- **Status:** accepted
- **Date:** 2026-06-28

## Context

`tessera.ingestion.chunk_text` — the engine's one source-neutral text chunker
(ADR 0008 frozen core) — splits a document into paragraph chunks on blank lines.
Markdown ATX headings (`#`…`######`) sit on their own line, blank-line-separated
from the body they introduce, so the chunker emitted a **standalone heading-only
chunk**: `## 2. Term and renewal` (one line) separate from its clause (the
`auto-renews` body three lines below).

BM25 length-normalises, so a four-token heading scores within ~0.05 % of its own
content clause on a renewal query. Milestone 10 recorded this as a real fragility:
appending four short disambiguation records shifted the corpus `avgdl` enough to
**flip the near-tie**, so the section *heading* out-ranked the actual *clause*. The
renewal retrieval test had to be relaxed from "the clause ranks top" to a top-2
invariant, and the root cause was filed as retrieval future work (STATUS
2026-06-28; the WRITEUP "Deliberately deferred" list). Milestone 11 takes it.

The same chunker is used by `sources/devex.py` for logs, so any change must not
move devex/github log chunk ids (committed gold cases pin them, e.g.
`run_R-1042:chunk5`).

## Decision

**A pure ATX-heading block leads the section it introduces** — `chunk_text` merges
it into the block that follows, so the heading becomes the lead line of its
section's first content chunk (line range contiguous, heading through content). The
heading's terms then *reinforce* its clause's retrieval score instead of competing
with it from a separate record.

**The heading predicate is `^#{1,6}[ \t]+\S`** — one to six `#`, then **at least
one space or tab**, then content. The mandatory whitespace is the safety boundary:

- It never matches GitHub-style runner-log markers (`##[error]`, `##[group]`,
  `##[endgroup]`) — `[` is not whitespace. So the shared chunker leaves devex logs
  (which use `chunk_text`) and github logs (which use `parse_log_chunks`) untouched;
  the log corpora contain no `^#{1,6}[ \t]+\S` lines (verified by `grep`).
- A bare `#`/`###` with no following content is not a heading and is not merged.

**Consecutive headings chain** onto the next content block; a **trailing heading**
with no following content stays its own chunk (a graceful edge case, absent from the
corpus). Ids stay the existing positional `<stem>:chunk<n>` — re-chunking the
business docs deliberately re-points the four affected gold ids (gold 01/03/07 and
`test_conflicts.py`), the same deliberate re-point Milestone 7's finer log chunking
made (ADR 0017).

## Consequences

- **Easier:** the renewal clause ranks #1 again and *stably* — the merged chunk
  carries both the heading terms and the clause, so corpus-size changes no longer
  flip it. The retrieval test is restored to the strict "the clause ranks top"
  assertion.
- **General, not business-specific:** any future Markdown source benefits; the rule
  is plain Markdown structure (a heading introduces the section beneath it).
- **Accepted cost — gold-id churn.** Heading-only chunks disappear, so business-doc
  chunk indices shift; the four references are re-pointed deliberately and pinned.
  devex/github ids are unchanged (proven; their corpora have no ATX headings).
- **Faithfulness untouched.** Re-chunking changes citable spans, not whether a
  claim is supported by its citation; the verifier and the floor are unaffected.
- **The line range can span the blank separator(s), and the text stays verbatim.**
  A merged heading+content chunk's range runs from the heading line through the
  content's last line, including the blank separator line(s) between them. The
  merged text is reconstructed from the **verbatim source span** (not a re-joined
  approximation), so the provenance invariant *a chunk's text covers exactly its
  reported line range* holds even when more than one blank line separates a heading
  from its content (pinned by a test). An earlier draft re-joined the blocks with a
  single blank line, which under-counted multi-blank gaps and would have made the
  cited line range over-claim the lines actually backing the text — caught by the
  pre-merge adversarial review and fixed.

## Alternatives considered

- **Fix it in `sources/documents.py` only.** Rejected: the defect is general
  Markdown structure, and the engine's one chunker is the honest place for it; a
  per-source patch would leave the next Markdown source exposed and split the
  chunking logic in two.
- **Down-weight heading tokens in BM25 (or add headings to the stop list).**
  Rejected: opaque and global, it would perturb ranking everywhere to fix one
  structural artefact. Chunking is the root cause; fix it there.
- **Keep the heading as an additional overlapping chunk.** Rejected for the same
  reason ADR 0017 rejected overlapping log chunks: it double-counts the section in
  retrieval and provenance.
- **A token/length threshold (only merge "short" heading-like blocks).** Rejected
  as more arbitrary than the structural predicate; an ATX heading is the real
  boundary, and the whitespace rule already excludes log markers.
- **Stemming so `renewal` matches `auto-renews`.** Rejected as orthogonal and far
  larger scope; the fix does not need it, and the deterministic, dependency-free
  retrieval posture (ADR 0003) is preserved.
