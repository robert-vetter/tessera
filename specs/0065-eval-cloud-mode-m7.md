# 0065. Eval cloud-mode for M7: the ER recall miss + the de-diluted synonymy case

- **Phase / milestone:** Milestone 7 — Unit 6 (of spec 0060)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

Units 2–5 built and proved the two M7 capabilities (embedding-assisted ER, finer
log chunking) without moving any public eval number. This unit makes the two wins
**recorded eval cases** — each an honest **offline miss** the batteries measure
and an **online close** the embeddings record (Unit 7), the M5/M6 trust-loop
shape applied to ER recall and log de-dilution.

## Acceptance criteria

- [ ] **Devex ER ownership gold case (09).** "Who is on call for
      checkout-service?" with `expected_support = [Component:SVC-CHK,
      Owner:checkout-svc]` and facts `[Storefront, Jonas Lindqvist]`. Offline
      (`difflib` leaves `checkout-svc` unresolved) the route answer is a faithful
      **partial** — it cites the catalog row but not the on-call — so faithfulness
      stays 1.0 while the case reads as a coverage/quality miss.
- [ ] **De-diluted gold-05.** Re-pointed from the run row to the isolated 404
      cluster: `expected_support = [27285174461.failed:error1]`, facts
      `[Not Found, Ensure GitHub Pages has been enabled]`. Offline lexical still
      returns nothing (zero token overlap) — the github_actions numbers are
      **unchanged** (coverage 0.833, quality 0.800); the de-dilution shows up
      online, where the answer surfaces the actual failure line, not the run row.
- [ ] **Offline numbers updated + pinned.** Devex gold reads coverage **0.950**,
      quality **0.889** (the recorded checkout-svc miss); faithfulness 1.0 on every
      battery. `test_devex_synthetic` updated to the new honest numbers.
- [ ] **Eval-level closes proven offline with stubs.** A test scores case 09
      through the route engine with a stub ER resolver (closes: cites both, renders
      both facts) and pins gold-05's de-diluted expectation.
- [ ] **Offline-miss point recorded.** `tessera-eval --record` appends the M7
      offline snapshot to `eval/history.jsonl` (devex 0.950/0.889, github_actions
      0.833/0.800, faithfulness 1.0) — the "before" of the trust-loop pair Unit 7
      closes online.
- [ ] **Gate green**; floor (faithfulness 1.0) holds.

## Scope

**In:** the devex gold case 09, the gold-05 re-point, the
`test_devex_synthetic` number update, the eval-close stub test, and the recorded
offline-miss history line. **Out:** the online run that records the closes (Unit
7); any harness/schema change (none needed — both cases ride the existing
route/lookup paths).

## Eval impact

- **Devex gold coverage 1.000 → 0.950, quality 1.000 → 0.889** — the recorded
  checkout-svc ER recall miss (the honest "before"; embeddings close it online).
- **github_actions gold unchanged offline** (0.833 / 0.800); gold-05's de-dilution
  is an online retrieval-quality win, recorded in Unit 7.
- **Faithfulness 1.0 everywhere**, at the miss and (Unit 7) the close.

## Risks / open questions

- **A public number drops.** Intended and on-brand (the M5/M6 "the eval can fail"
  ethos): a real, embedding-closable miss is recorded, not hidden. CI keeps the
  miss; the close is the timestamped online point.
- **The online close depends on the real model** surfacing the de-diluted error
  chunk / resolving the checkout-svc stem. The finer chunk makes it a sharp target
  and the stem coincides, so it is well-posed; Unit 7 measures and records it.
