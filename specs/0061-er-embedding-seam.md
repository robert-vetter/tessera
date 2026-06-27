# 0061. ER embedding seam: a semantic resolution regime, stem-gated for precision

- **Phase / milestone:** Milestone 7 — Unit 2 (of spec 0060)
- **Issue:** —
- **Status:** approved (autonomous mode; design recorded in **ADR 0016**)

## Problem

ER is pure-`difflib` character similarity at a 0.85 threshold
(`tessera/resolution.py`, `KnowledgeGraph.resolve_entities`). It misses
abbreviation variants that read as the same entity but differ as strings
(`checkout-service ↔ checkout-svc` = 0.846, just under the threshold), and it
*over-fires* on the opposite case where distinct firms collide on a shared
generic suffix (`… Logistik GmbH`, measured in `tests/test_scale.py`). Lowering
the global threshold trades one for the other catastrophically (ADR 0010/0015).

Milestone 6 brought real embeddings into the engine but kept them retrieval-only.
This unit builds the **seam** that lets a semantic signal *propose entity merges*,
designed against the opposite-direction tension: it must add recall
(`checkout-svc`) **without** worsening the generic-suffix over-merge. It does
**not** yet apply to any production graph (Unit 4) or measure precision/recall
(Unit 3) — it is the mechanism plus its design record, proven deterministically
offline.

## Acceptance criteria

- [ ] **New module `tessera/er_semantic.py`** that, given `(node_id, name)` pairs,
      an `EmbeddingProvider`, and a `VectorStore`, returns additive
      `graph.Resolution`s proposing same-entity merges. It **never** mutates a
      node and never touches the claim path.
- [ ] **Stem extraction + semantic threshold (the conjunction).** A merge is
      proposed only when the embedding cosine over the two names' **distinctive
      stems** (each name with its generic tokens removed) is `≥` a named, tunable
      threshold. The generic-token set = legal forms (reused from
      `tessera.resolution`) ∪ common org descriptors (`service`/`svc`/…) ∪
      corpus-frequent tokens (document frequency `≥` a named cutoff). So a high
      cosine coming purely from a shared generic suffix never triggers a merge.
- [ ] **Deterministic mechanism proof.** A test with a seeded keyword-axis **stub
      embedder** (no network) shows the proposer: merges `checkout-service ↔
      checkout-svc` (stems coincide after generic-stripping); merges a
      declaration-free **synonym** stem pair (`notif ↔ notifications`, the genuine
      embedding win); and does **not** merge the generic-suffix cohort
      (`Granite/Pyrite … Logistik GmbH`) or `Müller ≠ Nordwind Logistik` (their
      distinctive stems stay apart). Reproducible under varying `PYTHONHASHSEED`.
- [ ] **Reversibility + auditability preserved.** Each proposal is an ordinary
      `Resolution` with a `reason` naming the matched stems, the cosine, and the
      model, and a `confidence` = cosine — so when added to a graph it is
      inspectable and `remove_resolution`-reversible exactly like every other
      merge (ADR 0004).
- [ ] **Leak-guard extended + held.** `tessera.er_semantic` is added to the
      faithfulness verifier's banned import set (`tests/test_semantic.py`); the
      subprocess guard still passes (importing `eval.metrics` pulls no embedding/
      vector/provider/ER-embedding module). `graph`/`resolution`/`grounding`/
      `metrics` stay stdlib-only — the new module imports *them*, never the
      reverse.
- [ ] **ADR 0016** records the design (stem-embedding + generic-token gate,
      additive/reversible, retrieval-only line applied to ER, the opposite-
      direction tension and how the single rule resolves it), with the honest note
      on **where each gain comes from** (stem extraction is deterministic and
      closes `checkout-svc` offline; the model is what bridges non-identical
      synonym stems, declaration-free, and is the online-measured part).
- [ ] **Gate green** (format, lint, mypy strict, tests, faithfulness floor 1.0);
      offline numbers unchanged.

## Scope

**In:** the `er_semantic` module (tokenization, generic-token derivation,
distinctive-stem extraction, the embedding proposer), its stub-embedder unit
test, the leak-guard extension, and ADR 0016.

**Out:** applying the proposer to `build_devex_graph` / any battery (Unit 4); the
labeled precision/recall harness (Unit 3); the online HANA run (Unit 7);
multi-field ER (out of the whole milestone — name/stem signal only).

## Eval impact

None this unit (no graph wired to it yet); faithfulness floor unchanged at 1.0,
offline numbers byte-identical. The module is the mechanism Units 3–4/7 measure.

## Risks / open questions

- **Generic-token derivation brittleness.** A real distinctive token that happens
  to be corpus-frequent could be mis-stripped. Mitigated by: a named/tunable DF
  cutoff, an explicit small descriptor set for universal org words, and legal
  forms always-generic. Documented as a tunable knob (like the 0.85 threshold),
  not a solved problem — ADR 0016 states it.
- **Where the `checkout-svc` win really comes from.** Stem extraction (generic-
  stripping) makes `checkout-service` and `checkout-svc` reduce to the identical
  stem `checkout`, so that pair could close **deterministically** (no model).
  Stated honestly: the model's marginal value is bridging *non-identical* synonym
  stems (`notif ↔ notifications`) declaration-free — the online story. This unit
  proves both with the stub; Unit 4 gates the application behind
  `TESSERA_EMBEDDINGS` so CI's default keeps `checkout-svc` a named miss.
- **Leak-guard.** The one real hazard is an embedding import reaching
  `resolution.py` (on the verifier's closure via `normalize`). Avoided by keeping
  all embedding logic in `er_semantic` and importing *one-directionally*
  (`er_semantic` → `graph`/`resolution`/`platform`, never the reverse). The banned
  set gains the new module so a future violating edit fails loudly.
