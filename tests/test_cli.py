"""Tests for the CLI surface — the end-to-end hello-world path."""

import pytest

from tessera.cli import main
from tessera.grounding import REFUSAL_MESSAGE


def test_cli_demo_outputs_provenance(capsys: pytest.CaptureFixture[str]) -> None:
    """With no args, the demo question is auto-routed (to one-entity
    composition) and every claim is traced to an ingested source row."""
    exit_code = main([])
    out = capsys.readouterr().out
    assert exit_code == 0
    # The route is explained, the entity is resolved, provenance is visible.
    assert "[route: entity" in out
    assert "Mueller Logistik Gmbh" in out
    assert "salt_synthetic/" in out


def test_cli_refuses_unsupported(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["What colour is the sky?"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert REFUSAL_MESSAGE in out
