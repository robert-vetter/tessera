# 0035. Phase 4 plan: platform, polish, and the story

- **Phase / milestone:** Phase 4 — platform, polish, and the story (ROADMAP)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018: decisions recorded here instead of asked — except the two project-shaping questions below, which were asked)

## Problem

Phase 4 turns a measured engine into a presentable project: the deployment
path onto SAP infrastructure, the conversational surface polished into a
Joule-style experience, the technical write-up, and the debts Phase 3
deliberately recorded — the FIRED ADR 0003/0004 revisit triggers (devex gold
coverage 0.917, the named `notif-svc` miss) and the ADR 0008 namespace
asymmetry. This spec fixes the phase's unit breakdown and key decisions
upfront, as autonomous execution requires.

**Maintainer decisions (asked 2026-06-10, because external services/spend are
project-shaping):**

1. **SAP deployment path = docs + working code seams, no provisioning.**
   A deployment document with the exact AI Core / Generative AI Hub / HANA
   Cloud mapping and a provisioning runbook, plus real adapter code behind
   env config exercised by fakes in CI. Clone-and-run local mode stays the
   default; no cloud account is created this phase. This is the honest
   "designed to run on SAP, portable local mode" posture
   `docs/SAP_ALIGNMENT.md` endorses.
2. **LLM narration adapter targets SAP GenAI Hub, with an Anthropic API
   fallback** so narration is demoable locally today. Both optional and
   off by default; no key → deterministic rendering; CI stays key-free.

## Acceptance criteria

- [ ] The measured coverage gap is closed *first* (it is a public gold
      number): devex gold coverage 0.917 → 1.000 via deterministic catalog
      aliases, recorded with `tessera-eval --record`; the embeddings question
      (ADR 0003/0004 triggers) reassessed and decided in an ADR either way.
- [ ] The business answer layer lives beside `tessera/devex/` (the ADR 0008
      relocation), the business claim grammar is out of `eval/metrics.py`,
      the core is untouched, and **both batteries' numbers are pinned
      unchanged** through every refactor.
- [ ] A deployment path onto SAP AI Core / Generative AI Hub (models) and
      SAP HANA Cloud (graph/vector) exists as documentation + tested code
      seams; local mode remains the default and CI needs no keys.
- [ ] `uv run tessera` is a Joule-style conversational experience: explorable
      provenance, a visible trust signal, and optional LLM narration of
      verifier-checked claims (ADR 0006 trigger 2) that can never add facts.
- [ ] The technical write-up exists in the docs site: problem, approach,
      honest results including the coverage trail (business 0.929 → 1.000;
      devex 0.917 → final), limitations, future work.
- [ ] Phase close: docs pass the stranger test, CHANGELOG updated, gate green
      under multiple `PYTHONHASHSEED` values, STATUS wrapped, tagged
      `phase-4`.

## Scope

**In — the unit breakdown (one PR each, spec each):**

| Unit | Spec | Content |
|---|---|---|
| 1 | 0035 | this plan |
| 2 | 0036 | declared catalog aliases close the devex coverage gap; ADR 0010 (alias-first; embeddings reassessed) |
| 3 | 0037 | business answer layer relocates to `tessera/business/`; numbers pinned |
| 4 | 0038 | vertical-owned claim grammars leave `eval/metrics.py`; ADR 0011 |
| 5 | 0039 | SAP deployment path: docs + model-provider seam; ADR 0012 |
| 6 | 0040 | Joule-style surface: provenance exploration, trust signal, optional narration; ADR 0013 |
| 7 | 0041 | the technical write-up |
| 8 | 0042 | phase close: stranger-test docs, CHANGELOG, audit, wrap, tag `phase-4` |

**Out:** provisioning any cloud service or creating accounts (asked and
declined for this phase — the runbook makes it a later afternoon task);
agentic/MCP mode (named in `SAP_ALIGNMENT.md` as a future direction, not a
Phase 4 milestone — goes to the write-up's future work); real connectors;
fine-tuning/training; production security/multi-tenancy (ROADMAP's named
future work).

## Eval impact

Unit 2 moves **devex gold coverage 0.917 → 1.000** (the only intended metric
movement of the phase). Every other unit pins all eight recorded numbers
(faithfulness/coverage/quality × gold/synthetic × business/devex) unchanged;
any movement is a regression to fix, not to re-record.

## Risks / open questions

- The relocation (Units 3–4) touches many imports while promising identical
  numbers — mitigated by splitting module-move (0037) from grammar-move
  (0038) and pinning eval output before/after in each.
- LLM narration must be provably unable to add facts: narration is rendered
  *beside* verifier-checked claims, labeled, and guarded deterministically
  (a narration that introduces numbers/dates/ids absent from the claims is
  discarded in favor of deterministic rendering). The exact guard is ADR
  0013 material.
- ADR 0007 trigger 2 (battery saturation) is live — both synthetic batteries
  are green. Watched; if Phase 4 changes nothing there, the write-up names it
  as the next trust loop.
- Hash-seed flakes bit Phase 2; the close unit runs the gate under multiple
  `PYTHONHASHSEED` values before tagging.
