# 0056. Eval cloud-mode: the synonymy gold case, measured — miss offline, close online

- **Phase / milestone:** Milestone 6 — Embeddings on SAP (Unit 6 of 9; plan 0051)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

The seams (U2–U5) exist; now the eval must *measure* the embedding win. This unit
wires semantic retrieval into the harness (provider-agnostic) and adds the
**error-class-synonymy gold case** to the `github_actions` battery — the case
that makes the milestone's claim falsifiable:

- **Offline / CI (lexical):** a question phrased in pure out-of-log vocabulary
  ("is the published documentation site unreachable for visitors?") shares **zero
  content tokens** with the real Pages-deploy log (verified — the log says
  `HttpError: Not Found`, `status: 404`, `Ensure GitHub Pages has been enabled`,
  `Creating Pages deployment failed`, none of which the question names). Lexical
  BM25 returns nothing → the case is a **recorded miss** (coverage and quality
  drop; faithfulness stays 1.0).
- **Online (HANA-native embeddings, U8):** the concept maps to the Pages-deploy
  failure → the case **closes** (recorded in `eval/history.jsonl`).

This is the re-inverted criterion in one case: a real, undeclarable miss the
deterministic engine has, closed by semantics, both halves recorded.

## Acceptance criteria

- [ ] **Harness wiring (provider-agnostic):** `Battery.uses_semantic` flag; the
      harness builds a semantic index **once per battery** when configured (None
      offline) and threads it to `Battery.answer(case, graph, kb, index)`. Only
      `github_actions` sets `uses_semantic=True`; business/devex ignore the index
      (their behaviour is byte-identical).
- [ ] `retrieval.answer` factored into `answer_over(question, hits)` +
      `answer = answer_over(retrieve(...))`, so the devex/github_actions lookup
      path can answer over **semantic-or-lexical** hits with no claim-path change.
- [ ] **The synonymy gold case** (`github_actions/05`): `kind="answer"`,
      out-of-log vocabulary; expected support = the real Pages-deploy log chunk;
      expected fact = `HttpError: Not Found`. **Offline = refusal (miss).**
- [ ] **Tests pin both halves and the precision guard:** offline the case
      refuses and the battery shows faithfulness 1.0 with coverage/quality < 1.0
      (the recorded miss); given a stub-embedder index the **same** case answers,
      cites the Pages log, renders the expected fact (the close, mechanism);
      **precision** — the stub-semantic retrieval for the synonymy question does
      **not** surface the unrelated ruff-format failure (no cross-cause
      conflation).
- [ ] **The miss is recorded** in `eval/history.jsonl` with a `--note` marking it
      the offline/lexical synonymy miss (the close is U8). Faithfulness 1.0.
- [ ] The verifier leak-guard still passes (faithfulness stays structural and
      embedding-free).

## Scope

**In:** `Battery.uses_semantic` + `answer` signature (4th param) — vertical-neutral
eval wiring; harness index build/threading; `retrieval.answer_over`; registry
answer functions updated; the `github_actions/05` gold case; battery test updates
(count 4→5, the recorded-miss numbers, the stub-index close, the precision
guard); the recorded history point.

**Out:** the live run (U8 — where the *real* close is recorded with SAP's model);
the deployment runbook + dedicated user (U7); the GenAI Hub path (built, U2; not
exercised here). No engine claim path change — embeddings move retrieval only.

## Eval impact

**Intended, on purpose:** `github_actions` **gold coverage and quality drop below
1.0 offline** — the visible, recorded miss the milestone exists to surface (M5
precedent: the floor that can fail is the honest one). Faithfulness stays gated
at 1.0 on every battery; business/devex/synthetic unchanged. The recovery to
1.0 is U8's online recording.

## Risks / open questions

- **A permanent offline sub-1.0 is intended, not a regression.** The battery test
  pins it as such; STATUS/WRITEUP explain both halves of the trust-loop pair so a
  reviewer cloning at HEAD understands the offline miss is the point.
- **Shared `_devex_answer`** serves devex (always `index=None`) and
  github_actions (index in cloud). With `index=None` the path is exactly the
  prior lexical `answer` — devex numbers must not move (pinned).
- **Stub-embedder close is a mechanism test, not the result.** It proves the
  wiring closes the case given a model that groups the synonyms; SAP's model
  doing so is U8's recorded measurement.
- **Precision guard scope:** embeddings are retrieval-only, so ER is untouched
  (the `checkout-svc` near-miss + distinct-service separations stay as the devex
  ER tests already pin). The guard here is retrieval precision: no cross-cause
  conflation on the synonymy query.
