"""Tests for the CLI surface — the end-to-end hello-world path."""

import pytest

from tessera.cli import main
from tessera.grounding import REFUSAL_MESSAGE


def test_cli_demo_outputs_provenance(capsys: pytest.CaptureFixture[str]) -> None:
    """Running with no args answers the demo question by surfacing retrieved,
    sourced evidence."""
    exit_code = main([])
    out = capsys.readouterr().out
    assert exit_code == 0
    # The spotlight customer is surfaced, traced to an ingested SALT source row.
    assert "Müller Logistik GmbH" in out
    assert "salt_synthetic/" in out


def test_cli_refuses_unsupported(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["What colour is the sky?"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert REFUSAL_MESSAGE in out
