"""Tests for the eval-harness scaffold.

They pin the *honest* behaviour: with no gold set the harness says so and invents
no number; with cases present it counts them but still reports metrics as unset
until Unit 6 implements scoring. Exercising the harness here also keeps CI from
letting it silently bitrot.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tessera.eval.cli import main
from tessera.eval.harness import load_gold_set, run_eval


def test_run_eval_reports_no_gold_set_yet() -> None:
    report = run_eval()  # the real (empty) gold dir
    assert report.gold_case_count == 0
    assert not report.evaluated
    # No fabricated numbers.
    assert report.faithfulness is None
    assert report.coverage is None
    assert report.quality is None
    assert "no gold set evaluated yet" in report.summary()


def test_cli_runs_and_is_honest(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "no gold set evaluated yet" in out


def test_load_gold_set_empty_when_absent(tmp_path: Path) -> None:
    assert load_gold_set(tmp_path / "does-not-exist") == []


def test_counts_cases_but_still_reports_metrics_unset(tmp_path: Path) -> None:
    """Adding gold cases early must not fabricate metrics or crash the gate."""
    (tmp_path / "case1.json").write_text(json.dumps({"question": "Q?"}), "utf-8")
    cases = load_gold_set(tmp_path)
    assert len(cases) == 1

    report = run_eval(tmp_path)
    assert report.gold_case_count == 1
    assert report.faithfulness is None  # scoring is Unit 6
    assert "scoring not implemented yet" in report.summary()
