"""Tests pinning the Auditability Floor (spec 0137).

The two floors are strict-equality pinned so a slip fails the gate: 100%
re-derivation equality across every committed gold case (out-of-process),
and 100% mutation detection with the correct verdict class and a named
cause. The published block in ``docs/AUDITABILITY.md`` is byte-equal to a
fresh computation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tessera.eval.auditability import (
    DOC_BEGIN,
    DOC_END,
    AuditabilityReport,
    render_markdown,
    run_auditability,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "AUDITABILITY.md"


@pytest.fixture(scope="module")
def report() -> AuditabilityReport:
    # In-process for test speed; the out-of-process path is exercised by the
    # dedicated test below and by the CI determinism matrix.
    return run_auditability(out_of_process=False)


def test_re_derivation_equality_floor_is_100_percent(
    report: AuditabilityReport,
) -> None:
    assert report.equality_holds, "a committed gold-case bundle failed to re-derive"
    assert report.cases_passed == report.total_cases
    assert report.total_cases >= 25  # all three gold sets, none silently skipped


def test_mutation_detection_floor_is_100_percent(report: AuditabilityReport) -> None:
    undetected = [row.name for row in report.mutations if not row.detected]
    assert undetected == [], f"undetected mutations: {undetected}"
    assert len(report.mutations) >= 13  # 10 answer + 3 action classes


def test_every_mutation_names_a_cause_and_hits_its_class(
    report: AuditabilityReport,
) -> None:
    for row in report.mutations:
        assert row.observed_exit == row.expected_exit, row.name
        assert row.cause_named, row.name


def test_out_of_process_equality_matches(report: AuditabilityReport) -> None:
    """The true offline-stranger check: a fresh interpreter per bundle. Runs on
    the business battery only (speed); the CI matrix runs all three on 3 OSes."""
    from tessera.bundle.emit import build_bundle
    from tessera.eval.auditability import _verify_out_of_process
    from tessera.eval.harness import load_gold_set
    from tessera.eval.registry import batteries

    business = next(b for b in batteries() if b.name == "business")
    for case in load_gold_set(business.gold_dir):
        bundle = build_bundle("business", case.question)
        assert _verify_out_of_process(bundle) == 0, case.id


def test_published_doc_block_matches_fresh_run(report: AuditabilityReport) -> None:
    # Normalize newlines: `.gitattributes` pins LF, but a stray CRLF checkout
    # must not be mistaken for a stale block (the content is what is pinned).
    doc = DOC_PATH.read_text("utf-8").replace("\r\n", "\n")
    assert doc.count(DOC_BEGIN) == 1 and doc.count(DOC_END) == 1, (
        "docs/AUDITABILITY.md must contain exactly one generated block"
    )
    start = doc.index(DOC_BEGIN)
    end = doc.index(DOC_END) + len(DOC_END)
    published = doc[start:end]
    fresh = render_markdown(report)
    assert published == fresh, (
        "docs/AUDITABILITY.md is stale: regenerate with "
        "`uv run tessera-auditability --markdown`"
    )


def test_floor_is_provably_failable() -> None:
    """A deliberately weakened verify (one that ignores semantic problems) would
    make the mutation floor go red — proving the floor can fail. We simulate
    that by asserting a hand-built all-detected report holds, and a report with
    one undetected mutant does not."""
    from tessera.eval.auditability import MutationRow

    good = AuditabilityReport(equality=(), mutations=(MutationRow("m", 2, 2, True),))
    assert good.detection_holds
    bad = AuditabilityReport(equality=(), mutations=(MutationRow("m", 2, 0, False),))
    assert not bad.detection_holds
