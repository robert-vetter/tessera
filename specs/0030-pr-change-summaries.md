# 0030. PR change-summaries tied to motivating tickets

- **Phase / milestone:** Phase 3 — second vertical (DevEx Copilot), Unit 5
- **Issue:** —
- **Status:** approved (autonomous mode; decisions recorded here)

## Problem

The second DevEx milestone behaviour: *"what does this change actually
do?"* — a PR summarized from its actual diff, tied to the ticket that
motivated it (CAPABILITIES vertical B). The tie is the part that needs
verification machinery: "PR-201 was motivated by DEVEX-204" must be
checkable against evidence, not asserted — the shared-fragment shape
(spec 0029) already covers it with the ticket id as the fragment.

## Acceptance criteria

- [ ] `tessera/devex/summaries.py` — `summarize_change(question, graph)`:
      the PR's metadata row verbatim, each diff hunk verbatim (the summary
      is built *from* the diff, not around it), a **motivating-ticket link
      claim** in the shared-fragment grammar (the ticket id appears in both
      the PR row and the ticket row), and the ticket row verbatim.
- [ ] **Honest omission:** a PR that references no ticket (PR-205) gets a
      summary without link/ticket claims — nothing invented.
- [ ] Refusals with reasons: no PR named; unknown PR.
- [ ] Every emitted claim passes `is_supported`; a tampered link claim is
      rejected (adversarial test).
- [ ] Zero core changes.

## Scope

**In:** the summaries path + tests.
**Out:** routing/CLI (Unit 6); "which run failed on this PR's commit"
cross-links (the corpus supports PR-188 ↔ R-1018; recorded future work);
natural-language paraphrase of hunks (the diff *is* the summary's body —
prose synthesis without a verifier shape for it would be ungrounded).

## Eval impact

None yet; consumed by Unit 8's battery. Business numbers unchanged.

## Risks / open questions

- Hunk claims quote diff text verbatim — long but exactly citable; if the
  demo needs trimming later, trim the *display*, never the evidence.
