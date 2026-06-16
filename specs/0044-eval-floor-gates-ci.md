# 0044. The faithfulness floor gates the build (CI), not only `/verify`

- **Phase / milestone:** Milestone 5 — Hardening (spec 0043, unit 2)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

The project's headline claim is *the faithfulness floor gates the build* — a
claim below 1.0 fails it, locally and in CI (README, WRITEUP, ADR 0005). The
Milestone-5 reconnaissance found this is **not actually enforced by any automated
gate**:

- `scripts/gate.sh` runs format, lint, type-check, tests — **not** the eval.
- `.github/workflows/ci.yml` runs `bash scripts/gate.sh` + a gitleaks scan —
  **not** the eval.
- `uv run tessera-eval`'s non-zero exit on a floor breach runs **only** in the
  `/verify` command (`.claude/commands/verify.md` step 2), which is a manual
  agent step, not a check on any push or PR.

So the one hard floor is protected remotely only *indirectly*, by pytest
assertions (`test_eval.py` pins the numbers; `test_metrics.py` is the
falsifiability proof). A faithfulness regression that those pins did not happen
to cover would pass CI. Before this milestone deliberately makes the eval
*harder*, the floor must actually gate the build. (`gate.sh`'s own comment claims
the eval "is run separately by each caller, matching CI's job layout" — but CI
has no such step; the comment describes an intent the layout never fulfilled.)

## Acceptance criteria

- [ ] `scripts/gate.sh` runs `uv run tessera-eval` as its final step, so the
      faithfulness floor's non-zero exit fails the gate. Because `ci.yml` and
      `/verify` both run `gate.sh` (the single source of truth, spec 0016), the
      floor now gates **both** with no CI-vs-local divergence.
- [ ] A **forced floor breach fails the gate locally** — demonstrated (transient,
      reverted) and described, not just asserted.
- [ ] `gate.sh`'s comment is corrected to state the eval is part of the gate.
- [ ] `verify.md` is updated so it does not imply the eval runs *only* as a
      separate step (it now runs inside `gate.sh` step 1; the reporting/compare
      against `STATUS.md` stays).
- [ ] No metric moves; all eight recorded numbers unchanged (this unit adds a
      gate step, no behaviour change).

## Scope

**In:** add `uv run tessera-eval` (no `--record`) to `scripts/gate.sh`; fix the
two stale comments; a tiny note in `verify.md`.

**Out:** changing what the eval measures; `--record` in the gate (recording stays
a deliberate, `--note`-paired checkpoint at unit close); adding a separate eval
*job* to `ci.yml` (folding it into the shared `gate.sh` is the lower-divergence
choice — CI inherits it for free, exactly the property spec 0016 established).

## Eval impact

None. The numbers are unchanged; this unit makes the existing floor *enforced*
where the project always claimed it was. The point is procedural, not metric.

## Risks / open questions

- The eval now runs on every gate invocation (CI, `/verify`, and anyone running
  `gate.sh`). It is deterministic and fast (~0.2s over a few hundred cases), so
  the added gate cost is negligible.
- Ordering: the eval runs **after** pytest, so a code regression surfaces first as
  a unit-test failure (more localized) and the floor breach second (more
  holistic) — the more-actionable signal first.
