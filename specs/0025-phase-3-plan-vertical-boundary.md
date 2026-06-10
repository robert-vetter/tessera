# 0025. Phase 3 plan: the DevEx vertical on an unchanged core

- **Phase / milestone:** Phase 3 — prove generalization with the second vertical (ROADMAP)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018: decision recorded here instead of asked)

## Problem

Phase 3 must prove principle 5: the engine built for the Business Data Copilot
is *general*, not secretly business-shaped. That is only provable by running a
genuinely different vertical — the DevEx Copilot (CI/CD logs, PR diffs, ticket
history; CAPABILITIES Reference vertical B) — **on the same core, unchanged**,
and measuring it with the same eval discipline. This spec fixes the phase's
unit breakdown and key decisions upfront, as autonomous execution requires.

## Acceptance criteria

- [ ] CI/CD logs, PR diffs, and ticket history ingested through the **same**
      `Ingester` door into the **same** graph machinery (deterministic synthetic
      corpus, like `data/salt_synthetic`).
- [ ] Root-cause hypotheses for failed pipelines, grounded in log lines and
      linked to prior incidents; PR change-summaries tying diffs to their
      motivating tickets. Every claim carries provenance; every unanswerable
      question is refused with a reason.
- [ ] The eval harness runs a DevEx battery (own gold set + synthetic cases)
      alongside the business battery; the faithfulness floor (1.0) gates both.
- [ ] The core engine is **byte-identical to `phase-2`** except the two
      sanctioned vertical-neutral generalizations of ADR 0008 — proven by a
      recorded `git diff phase-2..phase-3` audit at phase close.
- [ ] Numbers recorded with `tessera-eval --record`; demo (`tessera-devex`)
      runnable; tagged `phase-3`.

## Scope

**In — the unit breakdown (one PR each, spec each):**

| Unit | Spec | Content |
|---|---|---|
| 0 | 0025 | this plan + ADR 0008 (vertical boundary) + ADR 0009 (multi-vertical eval) |
| 1 | 0026 | DevEx synthetic corpus + deterministic generator |
| 2 | 0027 | DevEx ingesters through the same door (new locator kinds) |
| 3 | 0028 | DevEx graph assembly + component entity resolution |
| 4 | 0029 | generic recurrence claim shape (verifier) + RCA answer path |
| 5 | 0030 | PR change-summary answer path |
| 6 | 0031 | DevEx routing + `tessera-devex` CLI door |
| 7 | 0032 | eval harness parameterized over batteries (business unchanged) |
| 8 | 0033 | DevEx gold set + synthetic battery; numbers recorded |
| 9 | 0034 | docs, CHANGELOG, core-frozen audit, wrap, tag `phase-3` |

**Out:** real CI/tracker connectors (GitHub/Jira APIs) — the corpus is
synthetic-but-schema-realistic, like SALT; LLM/embedding upgrades (their ADR
triggers are *watched*, and any newly measured miss is recorded, not silently
fixed); relocating the existing business modules (`composition`, `reasoning`,
`conflicts`, `knowledge`, `eval/synthetic`) into a `verticals/` namespace —
deferred to Phase 4 polish to keep this phase's diff honest (ADR 0008).

## Eval impact

Adds a second measured battery (DevEx gold + synthetic) under the same
faithfulness floor. Business numbers must not move. DevEx coverage is
expected **< 1.0** with *named* misses (the `-svc` abbreviation family scores
0.846, just under the 0.85 resolution threshold; vocabulary mismatch in
retrieval) — honest, improvable baselines that exercise ADR 0003/0004's
revisit triggers with real measurements.

## Risks / open questions

- The verifier and harness cannot express a second vertical without *any*
  change — the two sanctioned, vertical-neutral core deltas are an ADR-worthy
  finding, recorded as ADR 0008/0009 **before** implementation.
- Recurrence ("has this failure happened before?") must be verifiable without
  DevEx vocabulary in eval internals — solved by a generic quoted-fragment
  shape (ADR 0008), adversarially tested.
- Hash-seed flakes bit Phase 2; every unit's gate runs under multiple
  `PYTHONHASHSEED` values before merge.
