"""Tests for the eval harness over the curated gold set.

Pins the headline guarantees: faithfulness is 1.0 on the real gold set, coverage
is honestly below 1.0 (the Lumière miss), quality is reported, and the CLI fails
the build when faithfulness drops below its floor.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tessera.eval.cli import main
from tessera.eval.harness import EvalReport, load_gold_set, run_eval


def test_gold_set_is_loaded() -> None:
    cases = load_gold_set()
    assert len(cases) == 7
    assert {c.kind for c in cases} == {"answer", "refuse"}
    assert {c.engine for c in cases} == {"compose", "retrieve"}  # both answer paths


def test_faithfulness_is_one_on_the_gold_set() -> None:
    """Every emitted claim is supported by its cited evidence — the earned 1.0."""
    report = run_eval()
    assert report.faithfulness == 1.0


def test_coverage_is_complete_after_spec_0024() -> None:
    """Coverage reached 1.0 when the Lumière mention miss was closed (diacritic
    folding + suffix-tolerant mentions, spec 0024). The climb 0.929 -> 0.938 ->
    1.000 is recorded in eval/history.jsonl — the metric drove the fix."""
    report = run_eval()
    assert report.coverage == 1.0


def test_quality_is_reported() -> None:
    report = run_eval()
    assert report.quality == 1.0  # all six gold cases answered/refused correctly


def test_no_gold_set_reports_na(tmp_path: Path) -> None:
    report = run_eval(tmp_path)  # empty directory
    assert not report.evaluated
    assert report.faithfulness is None
    assert "no gold set evaluated yet" in report.summary()


def test_cli_passes_on_faithful_gold_set() -> None:
    assert main([]) == 0


def test_cli_fails_when_faithfulness_below_floor(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The hard floor: faithfulness < 1.0 makes the eval exit non-zero."""
    monkeypatch.setattr(
        "tessera.eval.cli.run_eval",
        lambda: EvalReport(
            gold_case_count=1, faithfulness=0.5, coverage=1.0, quality=1.0
        ),
    )
    exit_code = main([])
    assert exit_code == 1
    assert "FAIL" in capsys.readouterr().out
