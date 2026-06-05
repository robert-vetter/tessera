# 0009. Hello-world grounded-answer surface

- **Phase / milestone:** Phase 0 — Foundation and frame (the end-to-end skeleton)
- **Issue:** (none yet)
- **Status:** implemented

## Problem

`docs/ROADMAP.md` Phase 0 closes with "the smallest possible 'hello world' of
the conversational surface answering a hardcoded grounded question end-to-end —
proves the skeleton end-to-end before any real data." Units 1–8 built the
tooling; this unit is the first *product* code. It must demonstrate, in the
thinnest honest form, the project's two non-negotiable principles —
**provenance is mandatory** and **groundedness over fluency** (the system can
decline) — so that the shape it establishes is the shape Phase 1 grows into,
not something Phase 1 has to undo. It is deliberately **deterministic and
LLM-free**: a skeleton proving the path *question → evidence → grounded answer
with provenance → render*, runnable locally with no cloud or API key.

## Acceptance criteria

- [ ] A runnable surface (`uv run` entry point) answers **one hardcoded grounded
      question** end-to-end against a tiny, in-code set of evidence records.
- [ ] The answer carries **claim-level provenance**: every claim shows the
      specific source record(s) that justify it (record id + source + the
      supporting snippet), visible in the output — not a vague "sources" list.
- [ ] **Principled refusal works**: a question with no supporting evidence
      returns an explicit "not enough evidence" response, never a fabricated
      answer.
- [ ] The **core logic is importable** (a small module with typed
      evidence/claim/answer structures + an `answer()` function), with the CLI
      as a thin wrapper — so Phase 1 builds on it rather than around it.
- [ ] Tests assert the principles, not just output: (a) the grounded answer
      contains the expected claim **and** a non-empty provenance path for it;
      (b) **no claim is ever emitted without provenance**; (c) the refusal path
      triggers for unsupported questions.
- [ ] `/verify` is green; README documents how to run the demo.

## Scope

**In:** a small typed core (`EvidenceRecord`, `Claim`, `Answer`/provenance) with
an `answer()` function over a hardcoded evidence set; a thin CLI; tests that
encode the provenance/refusal invariants; a README "Try the demo" note.

**Out:** real ingestion, the knowledge graph, entity resolution, retrieval,
**any LLM call**, multi-turn conversation, general natural-language
understanding, more than the one demo question (+ a refusal case), the
**evaluation harness** (Phase 1), the web/Joule-style UI, and MCP. The data
structures are intentionally minimal and may be superseded in Phase 1.

## Eval impact

None yet — the eval harness arrives in Phase 1, so there is no faithfulness
number to move. **But this unit establishes the provenance contract the Phase 1
faithfulness metric will measure**: "every claim is supported by its cited
evidence." Encoding "no claim without provenance" as a test now is the honest
seed of that metric (it is a unit-test invariant here, not the eval).

## Risks / open questions

- **Surface choice** — **confirmed stdlib `argparse` CLI** (no new dependency,
  thinnest skeleton, fully reproducible) wrapping the importable core. Typer/HTTP/
  UI are Phase 1+. Cheap to reverse — **no ADR**.
- **Over-engineering the data model.** Risk of building a Phase 1 graph here;
  mitigated by keeping the structures minimal and explicitly provisional.
- **Provenance shape sets a small precedent.** The claim→evidence representation
  is the one durable design choice; worth getting *directionally* right so Phase
  1 extends it. If it proves load-bearing, an ADR can record it in Phase 1 — not
  needed for this throwaway-scale version.
