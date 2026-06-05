"""Tests for the CLI surface — the end-to-end hello-world path."""

import pytest

from tessera.cli import main
from tessera.grounding import REFUSAL_MESSAGE


def test_cli_demo_outputs_provenance(capsys: pytest.CaptureFixture[str]) -> None:
    """Running with no args answers the demo question, with ingested sources shown."""
    exit_code = main([])
    out = capsys.readouterr().out
    assert exit_code == 0
    # A claim and the ingested source records backing it both appear.
    assert "combined net value of those orders is EUR 45,000.00" in out
    assert "salt_synthetic/I_SalesDocument.csv" in out


def test_cli_refuses_unsupported(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["Who is Acme's CEO?"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert REFUSAL_MESSAGE in out
