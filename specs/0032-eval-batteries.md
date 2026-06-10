# 0032. The eval harness measures verticals as batteries

- **Phase / milestone:** Phase 3 — second vertical (DevEx Copilot), Unit 7
- **Issue:** —
- **Status:** approved (autonomous mode; implements ADR 0009)

## Problem

The harness is hardwired to one vertical (one graph, one KB, one engine
dispatch, one synthetic generator, one history line shape). Measuring the
DevEx vertical *requires* touching eval internals — ADR 0008's finding #2,
sanctioned as delta #2 and designed in ADR 0009. This unit performs the
parameterization **with the business battery only**, so the refactor's
correctness is itself measured: the business numbers must reproduce
exactly. The DevEx battery arrives in Unit 8.

## Acceptance criteria

- [ ] `eval/battery.py`: `GoldCase` (moved here; `harness` re-exports it so
      the frozen `eval/synthetic.py` import stays valid) + `Battery` (name,
      gold_dir, build_graph, build_kb, answer dispatch, synthetic
      generator).
- [ ] `eval/registry.py`: the **only** eval module importing vertical code;
      returns the battery tuple (business only, this unit).
- [ ] `eval/harness.py`: one vertical-neutral `_score`; `run_eval()` maps
      batteries → `BatteryResult`s; `EvalReport` holds the tuple;
      `floor_holds` spans every battery's gold + synthetic faithfulness.
- [ ] Gold files move to `eval/gold/business/` (content untouched).
- [ ] `eval/history.py` writes schema v2 (`"batteries": [...]`); existing
      v1 lines untouched and still loadable; the badge becomes the
      **minimum** gold faithfulness across batteries, green only while the
      floor holds everywhere.
- [ ] `tessera-eval` prints one line per battery per set; exits non-zero if
      *any* faithfulness < 1.0.
- [ ] **Regression equality:** business gold (7) and synthetic (52) all
      still 1.000 — byte-equal numbers, same case counts.

## Scope

**In:** the refactor + updated eval/history tests + gold relocation.
**Out:** the DevEx battery and gold set (Unit 8); any scoring-semantics
change (none — `_score` logic is moved, not modified).

## Eval impact

Numbers must NOT move; the unit fails if they do. Structure of the report
and history changes per ADR 0009.

## Risks / open questions

- `eval/synthetic.py` (frozen, ADR 0008) imports `GoldCase` from
  `tessera.eval.harness` — preserved via re-export; pinned by the suite
  staying green without touching that file.
- History consumers must tolerate v1 + v2 lines; `load_history` already
  returns raw dicts, and the badge-vs-journal test now reads both shapes.
