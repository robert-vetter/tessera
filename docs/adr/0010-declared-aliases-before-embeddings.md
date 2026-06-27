# 0010. Declared catalog aliases close measured ER misses; embeddings stay deferred

- **Status:** accepted
- **Date:** 2026-06-10

## Context

The ADR 0003 (lexical retrieval) and ADR 0004 (deterministic ER) revisit
triggers **fired** at the close of Phase 3 with a real measurement: devex gold
coverage 0.917, caused by the *named* `notif-svc` miss — the on-call export
abbreviates a service name (`notif-svc` vs `notifications-service`, similarity
0.429) in a way no string-similarity threshold can bridge without absurd
over-merge risk. Both ADRs promised that when the metric showed the
deterministic layer missing real links, embeddings (SAP Generative AI Hub +
HANA Cloud vector) would be reconsidered. Phase 4 must now decide: reach for
embeddings, or close the gap deterministically first?

A second fact weighs in: in real organizations this exact gap has a
non-ML, owned remediation — **the service catalog declares known aliases**.
The abbreviation is not unknowable; it is undeclared.

## Decision

**First loop: declared catalog aliases.** `components.csv` carries an
`Aliases` column; `SVC-NOTIF` declares `notif-svc`. The vertical asserts a
same-entity `Resolution` for each declared alias that **exactly equals**
(normalized) an existing name-bearing node — confidence 1.0 (declared data,
not an inference), reason naming the declaration, additive and reversible
like every other resolution (ADR 0004's model, unchanged). A new devex
*service route* answers ownership questions from the resolved entity's
records, so the closed ER gap becomes a closed coverage gap. The alias
matching is equality, never similarity — a declaration cannot transitively
bridge two distinct services.

**Embeddings: reassessed and deferred again, with a refreshed trigger.**
After the alias loop, no measured gap remains (devex gold coverage 1.000,
all faithfulness 1.000, synthetic batteries green). Adding an embedding
model now would buy zero measured improvement at the price of
non-determinism, a model/cloud dependency, and the clone-and-run guarantee.
The intended end state is unchanged — GenAI Hub embeddings + HANA Cloud
vector store with the lexical/string path as the portable local fallback
(ADR 0003) — and the **refreshed trigger** is: a measured gold/synthetic
coverage miss caused by vocabulary or name variance that *no one can fix by
declaring data* (no catalog/master field could carry it). Declared-but-
missed is a data bug; undeclarable-and-missed is the embeddings case.

**Deliberately retained near-miss:** `checkout-svc` (similarity 0.846, just
under the 0.85 threshold) stays **undeclared and unresolved**. It proves the
mechanism's honest boundary — aliases fix exactly what someone declares,
nothing more — and keeps a live, named specimen of the class of miss the
refreshed trigger watches for.

## Consequences

- **Easier:** the public gold number is repaired by reviewable data + a
  deterministic, citable assertion; the trust loop (measure → name the miss →
  fix → re-measure) closes end-to-end and is visible in `eval/history.jsonl`.
- **Easier:** clone-and-run, offline CI, and the auditable eval all survive
  untouched.
- **Accepted cost:** aliases are curation — every future abbreviation needs a
  declaration or it misses (that is the point: the miss is then a *named data
  gap*, not silent model behaviour).
- **Accepted cost:** alias assertion lives in the devex vertical
  (`tessera/devex/knowledge.py`), not the engine, until a second vertical
  needs alias data — generalizing from one data point is how cores rot
  (principle 5).
- The `Resolution.confidence` field now carries two regimes (similarity proxy
  vs declared 1.0); the `reason` string disambiguates, which is what it is
  for.

## Alternatives considered

- **Embeddings / semantic matching now.** Rejected: the only measured miss is
  closeable with declared data; embeddings would add cloud/model dependency
  and non-determinism for no measurable gain. The triggers stay live (and
  refreshed) — this is deferral with a criterion, not refusal.
- **Lower the resolution threshold (0.85 → 0.84) to catch `checkout-svc`.**
  Rejected: tuning a global threshold to rescue one pair invites transitive
  over-merge everywhere else (the worst cross-service similarity is already
  ~0.80) and would still not catch `notif-svc` at 0.429.
- **Hardcode the merge in vertical code.** Rejected: a co-reference fact is
  *data*; burying it in code makes it uninspectable and unreviewable, and the
  evidence text could not cite a declaring record.
- **Alias support inside the engine (`resolve_entities` reads aliases).**
  Rejected for now: only one vertical has alias data; the additive
  `Resolution` layer already expresses the assertion without any engine
  change. Promote when a second vertical needs it.

## Addendum (2026-06-27) — the refreshed trigger fired and is now acted on

Milestone 5 produced the undeclarable miss this ADR's refreshed trigger watched
for (the error-class synonymy in the real Pages-deploy log;
`test_adr0010_error_class_synonymy_is_undeclarable`). Milestone 6 acts on it —
GenAI Hub embeddings + HANA Cloud vector store, lexical path as the offline
fallback — with the boundary (retrieval-only, opt-in, faithfulness untouched)
recorded in **[ADR 0015](0015-embeddings-on-sap.md)**. This deferral has ended,
deliberately and with a measured cause.
