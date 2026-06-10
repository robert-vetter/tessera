"""The devex_synthetic corpus: deterministic, committed, and honestly difficult.

These tests pin the corpus *invariants* the DevEx vertical is built against
(spec 0026): byte-for-byte reproducibility (committed data == regeneration),
referential integrity across the six tables, and the planted-and-measured
difficulty (the recurring failure signatures, the PR↔ticket references, the
passing run that the RCA path must refuse to explain).
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "devex_synthetic"
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_devex_synthetic.py"


def _load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("generate_devex_synthetic", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _rows(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_committed_corpus_equals_regeneration(tmp_path: Path) -> None:
    """Clone-and-run honesty: the committed corpus is exactly what the
    committed generator produces — no hand edits hiding anywhere."""
    generator = _load_generator()
    generator.main(tmp_path)
    generated = sorted(
        p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file()
    )
    committed = sorted(
        p.relative_to(DATA_DIR) for p in DATA_DIR.rglob("*") if p.is_file()
    )
    assert generated == committed
    for rel in generated:
        assert (tmp_path / rel).read_bytes() == (DATA_DIR / rel).read_bytes(), rel


def test_referential_integrity() -> None:
    components = {row["Component"] for row in _rows("components.csv")}
    pipelines = _rows("pipelines.csv")
    assert {p["Component"] for p in pipelines} <= components
    pipeline_ids = {p["Pipeline"] for p in pipelines}
    runs = _rows("runs.csv")
    assert {r["Pipeline"] for r in runs} <= pipeline_ids
    assert {t["Component"] for t in _rows("tickets.csv")} <= components


def test_every_run_has_a_log_with_matching_verdict() -> None:
    for run in _rows("runs.csv"):
        log = (DATA_DIR / "logs" / f"run_{run['Run']}.log").read_text("utf-8")
        assert f"run {run['Run']}" in log
        assert run["Commit"] in log
        if run["Status"] == "failed":
            assert f"=== result: FAILED (job {run['FailedJob']})" in log
            assert "ERROR" in log
        else:
            assert "=== result: PASSED" in log
            assert "ERROR" not in log
            assert run["FailedJob"] == ""


@pytest.mark.parametrize(
    ("signature_attr", "run_ids"),
    [
        ("SIG_PAYMENTS_TIMEOUT", ("R-0987", "R-1042")),
        ("SIG_SEARCH_REPLICA", ("R-1023", "R-1031")),
    ],
)
def test_recurring_signatures_span_runs(
    signature_attr: str, run_ids: tuple[str, ...]
) -> None:
    """The recurrence anchors: one signature, several runs — the 'has this
    happened before?' question has a true answer in the data."""
    generator = _load_generator()
    signature = getattr(generator, signature_attr)
    for run_id in run_ids:
        log = (DATA_DIR / "logs" / f"run_{run_id}.log").read_text("utf-8")
        assert signature in log


def test_incident_ticket_quotes_the_payments_signature() -> None:
    generator = _load_generator()
    tickets = {t["Ticket"]: t for t in _rows("tickets.csv")}
    assert generator.SIG_PAYMENTS_TIMEOUT in tickets["DEVEX-187"]["Description"]
    assert generator.SIG_SEARCH_REPLICA in tickets["DEVEX-231"]["Description"]


def test_pr_ticket_references() -> None:
    """Every PR except PR-205 names its motivating ticket, and the named
    ticket exists; PR-205's missing reference is deliberate."""
    tickets = {t["Ticket"] for t in _rows("tickets.csv")}
    for pr in _rows("prs.csv"):
        referenced = {
            word.strip(":.,")
            for word in pr["Description"].split()
            if word.startswith("DEVEX-")
        }
        if pr["PR"] == "PR-205":
            assert not referenced
        else:
            assert referenced and referenced <= tickets


def test_payments_pipeline_has_a_passing_run_between_failures() -> None:
    """R-1041 passed after the mitigation and before the recurrence — the
    'why did this run fail?' refusal target is real, not hypothetical."""
    runs = {r["Run"]: r for r in _rows("runs.csv")}
    assert runs["R-1041"]["Pipeline"] == "PIPE-PAY"
    assert runs["R-1041"]["Status"] == "passed"
    assert runs["R-0987"]["Status"] == runs["R-1042"]["Status"] == "failed"


def test_pr_188_commit_is_the_commit_run_1018_failed_on() -> None:
    prs = {p["PR"]: p for p in _rows("prs.csv")}
    runs = {r["Run"]: r for r in _rows("runs.csv")}
    assert prs["PR-188"]["MergedCommit"] == runs["R-1018"]["Commit"]


def test_every_pr_has_a_diff() -> None:
    for pr in _rows("prs.csv"):
        diff = (DATA_DIR / "prs" / f"{pr['PR']}.diff").read_text("utf-8")
        assert diff.startswith("diff --git ")
