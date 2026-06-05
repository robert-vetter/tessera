"""Tests for the CLI surface — the end-to-end hello-world path."""

import pytest

from tessera.cli import main
from tessera.grounding import REFUSAL_MESSAGE


def test_cli_demo_outputs_provenance(capsys: pytest.CaptureFixture[str]) -> None:
    """Running with no args answers the demo question, with sources shown."""
    exit_code = main([])
    out = capsys.readouterr().out
    assert exit_code == 0
    # A claim and the source backing it both appear.
    assert "auto-renew in Q3 2026" in out
    assert "contracts.csv, row 2" in out


def test_cli_refuses_unsupported(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["Who is Acme's CEO?"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert REFUSAL_MESSAGE in out
