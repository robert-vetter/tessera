# 0062. ER precision/recall, measured on a labeled pair set

- **Phase / milestone:** Milestone 7 — Unit 3 (of spec 0060)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

There is no ER battery in the eval — the three batteries score answer-path
coverage/faithfulness, not merge correctness. The only ER measurement today is
`tests/test_scale.py` (cluster counts at volume) plus the pinned similarities in
`tests/test_devex_graph.py`. CLAUDE.md principle 3 says no capability is "done"
until its effect on the metrics is known; the embedding-assisted regime (Unit 2)
therefore needs an **ER precision/recall measurement** before Unit 4 applies it,
so its effect on *both* recall and precision is a measured fact, not a claim.

## Acceptance criteria

- [ ] **A labeled pair set** of truly-same and truly-distinct names, each pair
      annotated with its measured `difflib` similarity, covering: the recall
      misses (`checkout-service ↔ checkout-svc` 0.846; `notifications-service ↔
      notif-svc` 0.429), the cases `difflib` already gets (`search-servce` 0.960;
      `Payments Service` 1.000), the generic-suffix **over-merge** negatives
      (`Granite/Pyrite` 0.865; `Cobalt/Basalt` 0.889) and correctly-apart
      negatives (`Müller/Nordwind` 0.667; `checkout/payments` 0.600).
- [ ] **Precision/recall for three matchers**, computed and **pinned** (loud on
      drift): the `difflib` baseline, the stem-embedding regime (stub embedder),
      and their additive union (what Unit 4 deploys). Reported as a test — **not**
      a new gated eval floor (faithfulness stays the only hard floor).
- [ ] **The measured findings asserted:** the embedding regime adds the two
      recall misses (`recall(union) > recall(difflib)`); the embedding regime adds
      **no** false merge (the generic-suffix negatives are never merged by it, so
      its labeled precision is 1.0); and the union's precision gap is **entirely**
      `difflib`'s pre-existing generic-suffix over-merge — an additive regime
      cannot remove it.
- [ ] **The residual recorded honestly** in the spec and the test docstring: the
      generic-suffix over-merge is a `difflib` false positive; curing it needs the
      same stem-gating applied to the `difflib` pass (a deterministic engine change
      that would alter `resolve_entities`/`test_scale`, deferred) or multi-field ER
      (out of scope) — the stem-embedding regime already demonstrates precision 1.0,
      so the fix is known and named.
- [ ] **Deterministic** (stub embedder, fixed corpus); gate green; faithfulness
      floor unchanged.

## Scope

**In:** the labeled pair set, a small precision/recall scorer, the three matchers,
and the asserted/pinned numbers, all test-local (`tests/test_er_metrics.py`).

**Out:** a new gated eval metric / history-schema change; applying the regime to a
production graph (Unit 4); the online run (Unit 7); stem-gating the `difflib` pass
(the recorded residual's named next lever, not built here); multi-field ER.

## Eval impact

None on the gated eval (faithfulness/coverage/quality unchanged). This unit adds
a *reported* ER precision/recall measurement, the metric Unit 4's application is
judged against.

## Risks / open questions

- **Stub over-claiming.** The stub catches every positive because it is a toy that
  places synonym stems on a shared axis. Stated honestly: it proves the
  *mechanism* (a model that bridges synonym stems achieves the measured recall
  with no new false merges); the real model's recall is the recorded online run
  (Unit 7), not this test.
- **Precision is computed over labeled pairs** (a curated set), not the full
  pairwise space — standard for a labeled eval; noted in the test.
