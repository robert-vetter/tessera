# 0063. Apply embedding-assisted ER to the DevEx graph (recall closed, precision held)

- **Phase / milestone:** Milestone 7 — Unit 4 (of spec 0060)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

Unit 2 built the embedding-assisted ER regime and Unit 3 measured it on a labeled
pair set. This unit wires it into a **production graph** — the DevEx graph — so
the `checkout-svc` recall miss is actually closeable, while keeping the offline
default byte-identical and faithfulness gated at 1.0.

## Acceptance criteria

- [ ] **Vertical-side wiring behind the selector.** `build_devex_graph` runs a
      third additive regime after `difflib` + declared aliases, applying the
      embedding proposer over the graph's name nodes. The resolver is built from
      `TESSERA_EMBEDDINGS` (`none` → `None`, the default; `hana` → the
      HANA-native in-database path; `genai-hub` → provider+store), with all
      embedding imports **lazy** so the default import graph carries no cloud code.
      The engine `resolve_entities` stays embedding-free (the ADR 0010 precedent).
- [ ] **None-path byte-identical.** With no resolver (CI / offline default),
      `checkout-svc` stays the named miss it was; existing `test_devex_graph`
      assertions hold; the devex battery numbers do not move.
- [ ] **Recall closed (stub-proven).** With a seeded stub resolver,
      `Owner:checkout-svc` resolves into `Component:SVC-CHK`'s entity, so
      `service_lookup("Who is on call for checkout-service?")` surfaces the on-call
      (`Jonas Lindqvist`) and cites `Owner:checkout-svc`.
- [ ] **Precision held.** Distinct services never over-merge (`SVC-CHK` stays
      disjoint from every other catalog entity).
- [ ] **Reversible + auditable.** The embedding merge is an ordinary additive
      `Resolution` (reason names the stems/cosine/model, confidence in
      `[0.85, 1.0]`); withdrawing it re-splits `checkout-svc`.
- [ ] **Faithful under re-clustering.** Every claim the re-clustered ownership
      answer emits is `is_supported` — embeddings changed *what is linked*, never
      *what is claimed*. The offline partial answer is also faithful (the recorded
      miss is a coverage/quality gap, not a faithfulness one).
- [ ] **HANA-native path exercised offline.** A `propose_…_via_index` proposer
      (the in-database analogue, vectors never entering Python) is proven offline
      with an in-memory record index, reaching the same `checkout-svc` merge —
      so Unit 7 only flips the env on real HANA.
- [ ] **Gate green**, faithfulness 1.0, offline numbers unchanged.

## Scope

**In:** the `er_semantic` via-index proposer (shared core with the provider
proposer), `build_devex_graph`'s resolver step + the `TESSERA_EMBEDDINGS` factory,
and the offline stub tests.

**Out:** the devex ER **gold case** + the offline-miss recording (Unit 6, with the
de-diluted log case); the **online** run (Unit 7); business-vertical ER (its
`uses_semantic` stays off; the over-merge residual is the recorded ER finding,
Unit 3, and is not re-attacked here); stem-gating the `difflib` pass.

## Eval impact

None this unit — the devex battery still builds with `none` in CI, so its
faithfulness/coverage/quality stay 1.000. The recall close becomes a recorded
eval number in Units 6–7 (the offline-miss/online-close pair, the M6 pattern).

## Risks / open questions

- **Re-clustering desyncing faithfulness.** If embedding ER over-merged, the
  ownership answer (or a business superlative) could emit a claim the verifier
  rejects. Avoided here: the regime is precise (Unit 3), applied only to devex,
  and the answer only ever emits verbatim cited snippets; a dedicated test runs
  `is_supported` over the re-clustered answer.
- **Leak-guard.** The embedding imports are lazy and confined to
  `_devex_semantic_resolver_from_env`; `er_semantic` is already in the leak-guard
  banned set; `metrics.py`'s closure stays stdlib-only.
- **`build_devex_graph` now reads the environment.** Deliberate — it is how the
  online run flips the path; in CI the env is unset so behaviour is unchanged.
