# 0082. Heading-chunk retrieval fix

- **Phase / milestone:** Milestone 11, Unit 2 (the folded-in Milestone-10
  fragility — see spec 0081)
- **Issue:** the Milestone-10 close (STATUS 2026-06-28) + the WRITEUP "Deliberately
  deferred" entry: *"the heading-chunk retrieval fragility surfaced in Milestone 10
  (a Markdown section heading competes with its content in BM25) is filed as
  retrieval future work."*
- **Status:** approved (autonomous mode, per spec 0018)

## Problem

`tessera.ingestion.chunk_text` splits a document into paragraph chunks on blank
lines. A Markdown ATX heading sits on its own line, blank-line-separated from the
body it introduces, so the chunker emits a **standalone heading-only chunk** — e.g.
`## 2. Term and renewal` (line 12 of `mueller_logistik_msa.md`) as one chunk,
separate from its clause (lines 14–16, carrying `auto-renews`). BM25 favours short,
term-dense documents, so the four-token heading scores within ~0.05 % of its own
content clause on a renewal query. Milestone 10 recorded this when adding four short
disambiguation records shifted `avgdl` enough to **flip the near-tie**, forcing
`tests/test_retrieval.py::test_renewal_question_returns_the_actual_renewal_clause`
to be relaxed from a strict "the clause ranks top" assertion to a robust top-2
invariant. The root cause was filed as retrieval future work; Milestone 11 takes it
as the opening unit.

The defect is general, not business-specific: a lone section heading should *lead*
the section it introduces, never compete with it for retrieval rank.

## The fix

In `chunk_text`, after the existing blank-line split, **merge a pure ATX-heading
block into the block that follows it**, so the heading becomes the lead line of its
section's first content chunk (line range contiguous from the heading through the
content). A "pure ATX-heading block" is a single line matching `^#{1,6}[ \t]+\S` —
one to six `#`, then **at least one space/tab**, then content. The mandatory
whitespace is the safety boundary: it never matches GitHub-style log markers
(`##[error]`, `##[group]`) — `[` is not whitespace — and a bare `#`/`###` with no
content is not a heading either. Consecutive heading blocks chain onto the next
content block; a trailing heading with no following content stays its own chunk
(graceful edge case, absent from the corpus).

**Why in `chunk_text` (the ADR 0008 frozen core) and not in `documents.py`.**
`chunk_text` is the engine's one source-neutral text chunker; the fix is a general
Markdown-structure improvement and belongs where the chunking lives, so any future
Markdown source benefits. It is also used by `sources/devex.py` for logs — **proven
safe**: the devex/github log corpora contain **no** `^#{1,6}[ \t]+\S` lines
(`grep` verified), and github actually chunks with `parse_log_chunks`, not
`chunk_text`; so no devex/github chunk id shifts. This is a sanctioned, ADR-recorded
frozen-core change (ADR 0021), in the spirit of Milestone 7's finer log chunking
(ADR 0017) — a chunking improvement that re-points gold ids deliberately.

## Acceptance criteria

- [ ] `chunk_text` merges a pure ATX-heading block into its following content block;
      `^#{1,6}[ \t]+\S` is the heading predicate; `##[error]`-style markers and bare
      hashes are **not** headings (pinned by a test). The existing
      `test_chunk_text_splits_on_blank_lines_with_line_ranges` (no headings) stays
      byte-identical; new tests cover heading-merge, the `##[error]` non-match, a
      multi-heading chain, and a trailing-heading edge case.
- [ ] The business-doc chunk indices shift deterministically (heading-only chunks
      gone). The affected gold ids are **re-pointed**: gold 01 + 07
      `mueller_logistik_msa:chunk6 → :chunk3`; gold 07
      `mueller_logistik_amendment:chunk4 → :chunk2`; gold 03
      `lumiere_energie_letter:chunk4 → :chunk3`; `tests/test_conflicts.py`
      `chunk6/chunk4 → chunk3/chunk2`.
- [ ] `tests/test_retrieval.py::test_renewal_question_returns_the_actual_renewal_clause`
      is restored to a **strict** assertion: the **top** retrieved claim is the MSA
      renewal section, doc-span provenance, carrying `auto-renews` — no longer
      relaxed to top-2, because the heading no longer competes (the merged chunk
      carries both the heading terms and the clause, so it is a stable rank-1, robust
      to corpus-size changes).
- [ ] **No battery regresses.** Faithfulness 1.0 on all three batteries; business
      coverage/quality unchanged (gold 01/03/07 still resolve to their content);
      devex/github numbers **byte-identical** (their chunks do not move). Deterministic
      across `PYTHONHASHSEED` 0/1/42/2026.
- [ ] **ADR 0021** records the chunking decision (heading leads its section) +
      rejected alternatives. **Pre-merge 5-lens adversarial multi-agent review** — a
      frozen-core retrieval-ranking change is a coverage risk until proven.

## Scope

**In:** the `chunk_text` heading-merge; the chunker tests; the gold-id re-points
(business gold 01/03/07); the `test_conflicts.py` id update; the strict renewal
assertion; the battery-hold proof.

**Out:**
- **Any change to BM25 scoring, the stop list, or the retrieval ranking math.** The
  fix is purely at the *chunking* layer; ranking is untouched. (Rejected alternative:
  down-weighting heading tokens in BM25 — opaque and global; chunking is the honest
  root-cause fix.)
- **Stemming / lemmatisation** (`renewal`/`auto-renews`/`renew`). Out of scope; the
  fix does not depend on it.
- **Markdown structure beyond ATX headings** (setext headings, lists, tables). Only
  the `#`-heading-vs-content competition is in evidence; broader Markdown parsing is
  unwarranted scope.
- **The devex/github chunkers.** `parse_log_chunks` is unchanged; the shared
  `chunk_text` change is proven not to move their ids.

## Eval impact

- **Coverage / quality — held (a small honest ranking gain).** The renewal clause
  ranks top again; business gold 01/03/07 resolve to the same content via re-pointed
  ids, so their numbers are unchanged. devex/github numbers byte-identical.
- **Faithfulness — held at 1.0.** Re-chunking changes citable spans, not whether a
  claim is supported by its citation; the verifier is untouched.

## Risks / open questions

- **Gold-id drift is the central risk.** A missed re-point would drop a gold case's
  coverage. Mitigated by enumerating every `:chunk<n>` reference (done: gold 01/03/07
  + `test_conflicts.py:78` are the only business-doc references) and by the eval
  catching any uncaught drift (coverage < 1.0 fails the unit's intent).
- **The shared chunker touches devex logs.** Mitigated and proven: no ATX headings
  in the log corpora; devex/github chunk ids unchanged; pinned by their gold cases
  and the byte-identical battery numbers.
- **Restoring the strict assertion must reflect measured reality.** The strict
  top-1 assertion is written only after measuring that the merged renewal chunk
  ranks #1; if measurement showed otherwise, the assertion would name the measured,
  robust invariant honestly (it does rank #1 — the heading terms now reinforce the
  clause instead of splitting off).
