"""The real GitHub Actions battery, after the deterministic close (spec 0046).

Pins the recovered numbers and the valuable behaviour the close unlocked: RCA
over real 11-digit run ids, error chunks found by the real ``##[error]`` marker,
and a genuine cross-run recurrence (the two Pages-deploy 404 runs) — all
re-derived by the same faithfulness verifier the eval uses, none trusted.
"""

from __future__ import annotations

from tessera.devex.knowledge import build_github_actions_graph
from tessera.devex.rca import explain_failure
from tessera.eval.harness import BatteryResult, run_eval
from tessera.eval.registry import github_actions_battery


def _gh_result() -> BatteryResult:
    (result,) = run_eval([github_actions_battery()]).batteries
    return result


def test_github_actions_gold_recovered_to_one() -> None:
    result = _gh_result()
    assert result.gold_case_count == 4
    assert result.faithfulness == 1.0
    assert result.coverage == 1.0  # was 0.000 — the deterministic close
    assert result.quality == 1.0  # was 0.500
    assert result.synthetic_faithfulness == 1.0
    assert result.synthetic_coverage == 1.0


def test_rca_finds_real_run_by_numeric_id_and_github_error_marker() -> None:
    graph = build_github_actions_graph()
    answer = explain_failure("Why did run 27014662820 fail?", graph)
    assert answer.is_grounded
    rendered = answer.render()
    # The run row and the ##[error]-marked failed-step log are both surfaced.
    assert "Format check" in rendered
    assert "Would reformat" in rendered
    assert "Process completed with exit code 1" in rendered


def test_rca_detects_real_cross_run_recurrence() -> None:
    graph = build_github_actions_graph()
    answer = explain_failure(
        "Why did run 27285174461 fail, and has this happened before?", graph
    )
    assert answer.is_grounded
    recurrence = [c for c in answer.claims if c.text.startswith("Recurring failure:")]
    assert len(recurrence) == 1
    claim = recurrence[0]
    # The recurrence cites BOTH Pages-deploy runs' logs, sharing the signature.
    assert "Creating Pages deployment failed" in claim.text
    cited = {rec.id for rec in claim.support}
    assert "27285174461.failed:chunk1" in cited
    assert "27284786811.failed:chunk1" in cited


def test_passed_and_unknown_runs_refuse() -> None:
    graph = build_github_actions_graph()
    passed = explain_failure("Why did run 27411838436 fail?", graph)
    assert not passed.is_grounded and "did not fail" in (passed.refusal or "")
    unknown = explain_failure("Why did run 99999999999 fail?", graph)
    assert not unknown.is_grounded and "no run" in (unknown.refusal or "")
