"""Tests for the eval harness over the curated gold set(s).

Pins the headline guarantees: business faithfulness is 1.0 on the real gold
set, coverage/quality are reported, the CLI fails the build when any
battery's faithfulness drops below the floor, and the battery refactor
(spec 0032) reproduced the Phase 2 numbers exactly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tessera.eval.battery import Battery
from tessera.eval.cli import main
from tessera.eval.harness import BatteryResult, EvalReport, load_gold_set, run_eval
from tessera.eval.registry import GOLD_ROOT, batteries, business_battery


def test_business_gold_set_is_loaded() -> None:
    cases = load_gold_set(GOLD_ROOT / "business")
    # 9 → 10 (spec 0075): the same-name/different-address disambiguation refusal.
    assert len(cases) == 10
    assert {c.kind for c in cases} == {"answer", "refuse"}
    # compose, retrieve, and the routed multi-step path (the phrasing cases)
    assert {c.engine for c in cases} == {"compose", "retrieve", "route"}


def _business_result() -> BatteryResult:
    report = run_eval([business_battery()])
    (result,) = report.batteries
    return result


def test_business_numbers_hold_with_multifield_er() -> None:
    """The business numbers under the default multi-field ER (spec 0075): gold 10
    (the spec-0075 disambiguation refusal added) and synthetic 53, **all three
    metrics 1.0**. The metrics held through every refactor since Phase 2 (spec 0032)
    and through multi-field ER — the same-name pair refuses correctly under the
    address gate, so quality stays 1.0 (it is 0.900 under name-only ER, the recorded
    miss; see test_m9_multifield_close)."""
    result = _business_result()
    assert result.gold_case_count == 10
    assert result.faithfulness == 1.0
    assert result.coverage == 1.0
    assert result.quality == 1.0
    assert result.synthetic_case_count == 53
    assert result.synthetic_faithfulness == 1.0
    assert result.synthetic_coverage == 1.0
    assert result.synthetic_quality == 1.0


def test_empty_gold_dir_reports_na(tmp_path: Path) -> None:
    battery = Battery(
        name="empty",
        gold_dir=tmp_path,
        build_graph=business_battery().build_graph,
        build_kb=business_battery().build_kb,
        answer=business_battery().answer,
        synthetic=business_battery().synthetic,
    )
    report = run_eval([battery])
    assert not report.evaluated
    assert report.batteries[0].faithfulness is None
    assert "no gold set evaluated yet" in report.summary()


def test_every_registered_battery_is_named_in_the_summary() -> None:
    report = run_eval()
    summary = report.summary()
    for battery in batteries():
        assert f"[{battery.name}]" in summary


def test_cli_passes_on_faithful_gold_sets() -> None:
    assert main([]) == 0


def test_cli_recorded_flag_overrides_the_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``--recorded`` stamps a one-shot online measurement with an explicit date
    (spec 0066); without it the recorded date defaults to today. Patched so the
    real history file is never touched."""
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "tessera.eval.cli.record",
        lambda report, note, recorded=None: captured.update(
            note=note, recorded=recorded
        ),
    )
    assert main(["--record", "--recorded", "2026-06-27", "--note", "online"]) == 0
    assert captured == {"note": "online", "recorded": "2026-06-27"}


def test_cli_fails_when_any_battery_breaks_the_floor(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The hard floor spans batteries: one unfaithful battery fails the build."""
    faithful = BatteryResult(
        name="business", gold_case_count=1, faithfulness=1.0, coverage=1.0, quality=1.0
    )
    broken = BatteryResult(
        name="devex", gold_case_count=1, faithfulness=0.5, coverage=1.0, quality=1.0
    )
    monkeypatch.setattr(
        "tessera.eval.cli.run_eval",
        lambda: EvalReport(batteries=(faithful, broken)),
    )
    exit_code = main([])
    assert exit_code == 1
    assert "FAIL" in capsys.readouterr().out


def test_floor_also_gates_synthetic_faithfulness() -> None:
    report = EvalReport(
        batteries=(
            BatteryResult(
                name="x",
                gold_case_count=1,
                faithfulness=1.0,
                synthetic_case_count=1,
                synthetic_faithfulness=0.9,
            ),
        )
    )
    assert not report.floor_holds
