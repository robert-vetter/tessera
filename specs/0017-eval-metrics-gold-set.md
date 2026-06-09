# 0017. Evaluation metrics + curated gold set (close Phase 1)

- **Phase / milestone:** Phase 1 — final unit. Milestone: "the first version of the evaluation harness: a small gold set and a working faithfulness number, even if crude" (ROADMAP Phase 1; CAPABILITIES Pillar 4). Closes Phase 1.
- **Issue:** (none yet)
- **Status:** draft

## Problem

`tessera-eval` runs but reports "no gold set evaluated yet". The project's third
non-negotiable — *trust is measured* — is still unfulfilled: there is no number
for how faithful the system is. This unit turns the honest "n/a" into a real,
**auditable** faithfulness number (plus coverage and quality) over a small,
human-curated gold set, scored against the answers the engine actually produces
(retrieval + cross-source composition). The metric definitions are the project's
central contract, so **how** faithfulness is defined is recorded in an ADR.

The honest constraint: there is **no LLM** in this slice (ADR 0003), so
faithfulness is measured **structurally/deterministically**, not by a model
judge. That bounds what the number proves — and the ADR must say so plainly.

## Definitions (decided; recorded in ADR 0005)

- **Faithfulness** — of all claims the system emits across the gold questions, the
  fraction whose content is **deterministically supported by their cited
  evidence** (a surfaced snippet appears in its cited record; an aggregate equals
  the computation over exactly its cited rows; an identity claim's counts match
  its cited records) — **a check that is provably able to fail, demonstrated by a
  test that injects a known-unfaithful claim and asserts the metric catches it.**
  The adversarial-failure proof is **part of the definition**, so the score is an
  *earned* 1.0, not a tautological one. **Hard floor: faithfulness < 1.0 fails the
  build** — an unsupported claim is a failure, not a low score.
- **Coverage** — over answerable gold cases, the fraction of the gold's **expected
  supporting evidence** that the answer actually surfaces. **Reported, not gated**,
  and expected to be **< 1.0** (e.g. the Lumière mention miss is a known,
  documented coverage gap) — an honest, improvable number.
- **Quality** — the fraction of gold cases answered **correctly** (answerable: the
  expected key fact/value is present; refusal: the system refuses). **Reported,
  not gated.**

## Acceptance criteria

- [ ] A small **curated gold set** under `eval/gold/` (committed JSON), each case
      human-checked, covering: cross-source composition (Müller: total + agreement
      clause), a structured retrieval lookup, the **mixed-currency** refuse-to-sum
      case, an **ambiguous** question (refusal), and an **out-of-scope** question
      (refusal). Documented so the metric is auditable.
- [ ] `tessera.eval` **computes the three metrics** over the gold set against the
      engine's real answers (retrieval and/or composition), filling the `None`s
      from the Unit-1b scaffold; `run_eval()` returns the populated `EvalReport`.
- [ ] `uv run tessera-eval` reports the three numbers; **faithfulness < 1.0 exits
      non-zero** (a real gate), while coverage/quality are reported as tracked
      targets (not hard-failed).
- [ ] A test **injects a known-unfaithful claim** (content not supported by its
      cited evidence) and asserts the faithfulness metric **catches it** (score
      < 1.0) — the earned-not-tautological proof, part of the faithfulness
      definition.
- [ ] The metric definitions and the gold-set format are **documented and
      transparent** (auditable, not a black box), and **ADR 0005** records the
      faithfulness definition (including the adversarial-failure proof as part of
      it), the no-LLM structural approach, and **what the number does and does not
      prove**.
- [ ] The numbers are recorded in `docs/STATUS.md` (first real eval line), and the
      faithfulness/coverage badges noted in README as now meaningful.
- [ ] Gate green (`bash scripts/gate.sh`); `tessera-eval` green (faithfulness 1.0).
      Tag `phase-1` at the end (closes the phase).

## Scope

**In:** the gold-set data + loader extension; the three metric computations;
`tessera-eval` reporting + faithfulness exit-code gate; the ADR; STATUS/README;
the `phase-1` tag.

**Out:** **synthetic gold-data generation** (Phase 2 — this gold set is small and
hand-curated); **LLM-judged** faithfulness (ADR 0003; future work); regression
**history/trend storage** over time (Phase 2); wiring eval into `scripts/gate.sh`
as a hard CI blocker beyond the faithfulness floor (coverage/quality stay
reported); new engine behaviour.

## Eval impact

This **is** the eval. It produces the first real faithfulness / coverage / quality
numbers. Direction: faithfulness should read **1.0** (the structural invariant
holds by construction; the metric's job is to keep it there); coverage/quality
will be **honest fractions < 1.0** that later units improve. No prior numbers to
regress against — this sets the baseline.

## Risks / open questions (decisions recorded)

- **Faithfulness definition — decided:** structural support check **+ adversarial
  guard as part of the definition** (provably able to fail; demonstrated by an
  injected-unfaithful-claim test). The earned 1.0. → ADR 0005.
- **Gating — decided:** faithfulness gates (hard floor 1.0); coverage and quality
  are reported, not gated. Coverage is *expected* < 1.0 (the Lumière miss).
- **Gold set — decided:** five cases — both answer paths (cross-source compose +
  structured lookup) and all three refusal kinds (mixed-currency, ambiguous,
  out-of-scope).
- **What the number proves (must be honest in ADR 0005):** a deterministic
  structural check is a strong *regression guard* and a real provenance proof, and
  the adversarial test shows it can fail — but it is **not** the semantic
  faithfulness a model judge would assess. LLM-judged faithfulness is future work
  (consistent with ADR 0003).
