# 0046. Real-data RCA: the measured un-planted miss, then its deterministic close

- **Phase / milestone:** Milestone 5 — Hardening (spec 0043, unit 4)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

The GitHub Actions connector (spec 0045) ingests real CI runs but no battery
measures them yet. This unit makes the eval **fail again on un-planted data** and
then closes the deterministic part of the miss — the project's trust loop
(*measure → name the miss → fix → re-measure → record*) applied, for the first
time, to data the project did **not** author.

The miss is real and three-fold, all confirmed against the snapshot:

1. The router/RCA run-id grammar is `R-\d{3,5}` — it cannot match an 11-digit
   GitHub run id, so RCA refuses to even find the run.
2. The error-line detector keys on a bare `ERROR`; real logs mark failures
   `##[error]`, so no error chunk is found and RCA collapses to the run row.
3. The signature extractor keys on `ERROR <token>:`; real `##[error]` lines do
   not match, so cross-run recurrence is never detected.

## Acceptance criteria

- [ ] A `github_actions` battery (gold + synthetic) is registered, reusing the
      DevEx answer dispatch over the **separate** real-data graph (spec 0045).
- [ ] **The miss is measured and recorded.** With the engine unchanged, the GH
      gold battery reports **coverage 0.000, quality 0.500** (and synthetic
      coverage 0.000) while **faithfulness stays 1.000** (the floor holds, the
      gate is green). This drop is recorded to `eval/history.jsonl` *on purpose* —
      the visible evidence the eval can fail again.
- [ ] **The deterministic part is closed, additively:** the run-id grammar also
      accepts GitHub numeric ids; the error detector also recognizes `##[error]`;
      the signature extractor also reads the first `##[error]` line. All three are
      *additions* — the synthetic DevEx logs still match the original `ERROR`
      shape — so **all eight existing recorded numbers stay byte-identical**.
- [ ] After the close, GH gold **coverage 1.000, quality 1.000**, faithfulness
      1.000, including a real **cross-run recurrence** claim (the two Pages-deploy
      404 runs share the `Creating Pages deployment failed` signature) — re-derived
      by the same shared-fragment verifier, not trusted. Recorded.
- [ ] Tests pin both the recovered GH numbers and the no-regression of the
      synthetic verticals.

## Scope

**In:** the battery + 4 gold cases + the data-derived GH synthetic generator; the
two recorded history points (drop, recovery); the additive engine close in
`devex/rca.py`; tests.

**Out:** free-form phrasing / verb-intent routing (spec 0048); multi-hop chains
(spec 0047); any LLM/embedding (determinism line); closing the **undeclarable**
real-data misses — the error-class synonymy (`HttpError: Not Found` =
`status: 404` = `Ensure GitHub Pages has been enabled`) and step-label synonymy
(`gate` / `Format check` / `ruff format`) are retained as the embeddings-trigger
specimens consolidated in spec 0050 (ADR 0010's refreshed criterion), **not**
closed here.

## Eval impact

The intended, recorded shape of this unit:

| point | github_actions gold | note |
|---|---|---|
| drop | faithfulness 1.000 · **coverage 0.000** · **quality 0.500** | real-data miss measured |
| close | faithfulness 1.000 · **coverage 1.000** · **quality 1.000** | deterministic recovery |

Business and DevEx batteries: all eight numbers **unchanged** at both points
(the close is additive). Faithfulness 1.000 everywhere, always.

## Risks / open questions

- **Recording a deliberately-degraded number** (the drop) is intentional and
  documented; the gate never goes red because faithfulness holds and coverage is
  reported, not gated. A reviewer cloning at the drop record sees an honest
  sub-1.0 coverage with a `--note` explaining it.
- **Signature over-link** (the maps' trap): `Process completed with exit code 1`
  is generic, but in this snapshot it is unique to the ruff run (verified), and
  the shared-fragment verifier would reject any recurrence claim citing a record
  that does not contain the fragment. The first `##[error]` line is used as the
  signature precisely because it is the most specific (`Creating Pages deployment
  failed`), not the generic trailer.
- **The additive close must not move the synthetic numbers** — pinned by
  `test_devex_synthetic` / `test_eval` and re-verified in the gate before/after.
