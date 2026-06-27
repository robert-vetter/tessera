# 0016. Embedding-assisted entity resolution: stem-gated, additive, retrieval-only

- **Status:** accepted
- **Date:** 2026-06-27

## Context

Entity resolution (ADR 0004) is deterministic, name-only, `difflib` character
similarity at a 0.85 threshold. ADR 0003/0004/0010 deferred embeddings behind a
**measured** trigger; Milestone 6 (ADR 0015) brought real SAP HANA embeddings
into the engine but confined them to **retrieval**. Two ER misses remained,
measured and recorded:

- `checkout-service ↔ checkout-svc` = **0.846** — a recall miss just under the
  threshold; an abbreviation gap character similarity cannot bridge
  (`tests/test_devex_graph.py`), kept as the named near-miss.
- The generic-suffix firms (`… Logistik GmbH`) **over-merge** at volume — a
  precision error reproduced in `tests/test_scale.py` (the shared suffix
  dominates the character ratio so distinct firms collapse).

These pull in **opposite directions**: recall wants *more* merging, precision
wants *less*. A naive name-cosine pass closes `checkout-svc` and makes the
over-merge **worse** — `Granite Logistik GmbH` and `Pyrite Logistik GmbH` are
semantically near-identical (same industry token + legal form), so a full-name
embedder rates them close. Lowering the global threshold was already rejected
(ADR 0010): no threshold bridges a 0.846 abbreviation without catastrophically
collapsing the generic-suffix cohort. The maintainer authorized acting on the
embedding trigger for ER (the Milestone-7 scope question, answered 2026-06-27):
**close the recall miss and attempt the over-merge with embeddings, recording the
residual honestly** if one rule cannot do both.

## Decision

**A second, additive resolution regime that proposes merges from the cosine of
the two names' _distinctive stems_.** It lives in a new module
`tessera/er_semantic.py`, alongside — never replacing — the deterministic
`difflib` pass.

- **Embed the stem, not the full name.** Each name is reduced to its *distinctive
  stem* by removing **generic tokens**: legal forms (reused from
  `tessera.resolution.LEGAL_SUFFIXES`) ∪ a small explicit set of universal
  organizational descriptors (`service`/`svc`/`system`/…) ∪ tokens whose
  **corpus document frequency** is at/above a named cutoff (so `Logistik` across
  four firms becomes generic without anyone naming it). A merge is asserted only
  when the **stem** cosine is at/above a named, tunable threshold
  (`DEFAULT_SEMANTIC_THRESHOLD = 0.85`).
- **One rule resolves the tension.** `checkout-service` and `checkout-svc` reduce
  to the identical stem `checkout` → merge (recall). `Granite Logistik GmbH` and
  `Pyrite Logistik GmbH` reduce to `granite` / `pyrite` → stay apart (precision).
  `notif-svc` and `notifications-service` reduce to `notif` / `notifications`,
  which a real model places close → a **declaration-free** synonym bridge.
- **Additive and reversible (ADR 0004 unchanged).** Each proposal is an ordinary
  `graph.Resolution` with a `reason` naming the matched stems, the cosine, and the
  model, and a `confidence` = cosine. The caller adds it to the graph; resolved
  entities stay derived connected components; `remove_resolution` re-splits. The
  module **never mutates a node** and returns proposals — it does not own the
  graph.
- **Retrieval/linking only — the ADR 0015 line, now applied to ER.** A semantic
  vector decides *which name nodes co-refer*; it never generates, alters, or
  judges a claim. The faithfulness verifier (`eval/metrics.py`) imports nothing
  from `er_semantic`; the leak-guard banned set includes it, and the module
  imports `graph`/`resolution`/`platform` **one-directionally** (they never import
  it), so a 1.0 stays earned by structure, not by a model.
- **Where each gain comes from, stated honestly.** Stem extraction is
  deterministic and does real work on its own: it closes `checkout-svc` (the stems
  become string-identical) and prevents the generic-suffix over-merge. The
  *model* earns only the cases where distinctive stems are **synonyms but not
  string-identical** (`notif ↔ notifications`) — the part that needs the online
  run and the part this regime adds over a pure stoplist. The milestone records
  the offline-reproducible part and the online-only part separately.

## Consequences

- **Easier:** the `checkout-svc` recall miss becomes closeable without lowering
  the threshold, and the generic-suffix over-merge is *attacked by the same rule*
  rather than worsened. Recall and precision are both measurable (Unit 3 harness).
- **Easier:** the assertion model needed **no change** — `Resolution`'s `score`/
  `confidence`/`reason` already carry an embedding score; the new regime is the
  third one (difflib match, declared alias, embedding match), all additive and
  reversible.
- **Accepted cost — generic-token derivation is heuristic.** A real distinctive
  token that is corpus-frequent could be mis-stripped. Bounded by a small, named,
  tunable DF cutoff + an explicit descriptor set + always-generic legal forms;
  documented as a revisitable knob (like the 0.85 threshold), not a solved
  problem.
- **Accepted cost — the online number is not CI-reproducible.** The synonym-stem
  bridge depends on the cloud model (`SAP_NEB.20240715`), which can change; that
  close is a **timestamped** point (the ADR 0015 precedent). CI stays on the
  deterministic path, where `checkout-svc` honestly remains a named miss because
  the application is gated behind `TESSERA_EMBEDDINGS` (Unit 4).
- **Accepted cost — re-clustering flows through faithfulness.** Embedding-assisted
  ER changes `graph.clusters()`/`entity_of`, which the business verifier shapes
  recompute over. If it over-merged, a superlative/compare claim's recomputed
  result would diverge and the floor would catch it — by design. Composition and
  verification must agree on the same graph; the regime is applied only where it
  is measured, and business `uses_semantic` stays False by default.
- ADR 0010's refreshed embeddings trigger is now **acted on for ER**; ADR 0003's
  "semantic deferred" is partially superseded *for ER linking on the embedding
  path only*. The deterministic `difflib` ER it chose remains the offline default.

## Alternatives considered

- **Embed the full name; gate on a shared distinctive token.** Rejected: it makes
  the embedding redundant for `checkout-svc` (they literally share `checkout`) and
  *rejects* the genuine win (`notif-svc ↔ notifications-service` share no token).
  Stem-embedding both closes the synonym case and keeps the precision gate.
- **Lower the global `difflib` threshold.** Already rejected in ADR 0010 and still:
  no threshold bridges a 0.846 abbreviation without collapsing the generic-suffix
  cohort. The miss is a metric/vocabulary problem, not a tuning problem.
- **Multi-field ER (name + address/attributes).** The ADR 0004 future-work lever,
  and the stronger precision tool — but a larger change, and the maintainer chose
  the embedding route this milestone. Kept on record as the named next lever **if**
  stem-embedding cannot close the over-merge without precision loss (the recorded
  residual).
- **An embedding signal inside `KnowledgeGraph.resolve_entities` (engine-level).**
  Rejected for the same generality reason ADR 0010 kept declared aliases
  vertical-side: it would pull an embedding import toward the verifier's closure
  (`graph`/`resolution`) and risk the leak-guard. The regime stays a separate
  module, applied vertical-side (Unit 4), mirroring `_assert_declared_aliases`.
- **Embeddings on the claim/faithfulness path.** Rejected — that is ADR 0005's
  question, deferred. Faithfulness stays structural and embedding-free.
