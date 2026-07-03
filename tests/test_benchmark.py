"""The Faithfulness Floor benchmark (spec 0122): the pins that let it fail.

Four guarantees, each a build failure when broken:

1. **Doc pin** — the tables published in ``docs/BENCHMARK.md`` are byte-equal
   to a fresh run, so the public artifact cannot drift from measurement.
2. **Direction pin** — the gated engine's trustworthy-outcome rate is
   *strictly* above the ungated baseline's on every battery and case set;
   the headline claim is not allowed to outlive its truth.
3. **Equality pin** — the benchmark's gated side reproduces the offline eval
   numbers exactly (same harness, same corpora — a divergence means the
   benchmark stopped measuring what the project publishes).
4. **The seam is honest** — the ungated variant swaps ONLY the answerer;
   corpus, gold cases, synthetic generator, and claim shapes stay the
   original battery's own.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tessera.eval.benchmark import (
    DOC_BEGIN,
    DOC_END,
    BenchmarkReport,
    CaseOutcome,
    render_markdown,
    run_benchmark,
    ungated_answer,
    ungated_variant,
)
from tessera.eval.registry import batteries, business_battery
from tessera.grounding import KnowledgeBase

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "BENCHMARK.md"

# The benchmark is pinned offline (index=None on both sides); the eval-equality
# pin additionally compares against run_eval(), which DOES honour a configured
# embeddings environment. CI is key-free so the comparison is stable there;
# skip only in a deliberately configured online environment.
_ONLINE = os.environ.get("TESSERA_EMBEDDINGS", "none").lower() not in ("", "none")


@pytest.fixture(scope="module")
def report() -> BenchmarkReport:
    return run_benchmark()


def test_published_tables_match_fresh_run(report: BenchmarkReport) -> None:
    """Doc pin: regenerate the block and compare byte-for-byte."""
    doc = DOC_PATH.read_text("utf-8")
    assert DOC_BEGIN in doc and DOC_END in doc, "docs/BENCHMARK.md lost its markers"
    start = doc.index(DOC_BEGIN)
    end = doc.index(DOC_END) + len(DOC_END)
    published = doc[start:end]
    fresh = render_markdown(report)
    assert published == fresh, (
        "docs/BENCHMARK.md is stale: regenerate the block with "
        "`uv run tessera-benchmark --markdown` and commit it in the same PR "
        "as whatever moved the numbers."
    )


def test_gap_direction_holds_on_every_battery_and_set(report: BenchmarkReport) -> None:
    """Direction pin: strictly greater everywhere, named on failure."""
    for row in report.rows:
        assert row.tessera.trustworthy > row.ungated.trustworthy, (
            f"{row.battery} · {row.case_set}: gated {row.tessera.trustworthy:.3f} "
            f"is not strictly above ungated {row.ungated.trustworthy:.3f} — "
            "the headline claim of docs/BENCHMARK.md no longer holds; "
            "record the finding, do not massage it."
        )
    assert report.gap_holds_everywhere


@pytest.mark.skipif(_ONLINE, reason="online embeddings env: run_eval() != offline pin")
def test_gated_side_reproduces_the_offline_eval_numbers(
    report: BenchmarkReport,
) -> None:
    """Equality pin: the benchmark's Tessera column IS the eval, offline."""
    from tessera.eval.harness import run_eval

    eval_report = run_eval()
    by_name = {result.name: result for result in eval_report.batteries}
    for row in report.rows:
        result = by_name[row.battery]
        if row.case_set == "gold":
            expected = (result.faithfulness, result.coverage, result.quality)
            count = result.gold_case_count
        else:
            expected = (
                result.synthetic_faithfulness,
                result.synthetic_coverage,
                result.synthetic_quality,
            )
            count = result.synthetic_case_count
        assert row.case_count == count
        assert (
            row.tessera.faithfulness,
            row.tessera.coverage,
            row.tessera.quality,
        ) == expected, f"{row.battery} · {row.case_set} diverged from run_eval()"


def test_gated_faithfulness_is_state_of_the_floor(report: BenchmarkReport) -> None:
    """The gated side holds the 1.000 floor inside the benchmark too."""
    for row in report.rows:
        assert row.tessera.faithfulness == 1.0


def test_ungated_variant_swaps_only_the_answerer() -> None:
    base = business_battery()
    variant = ungated_variant(base)
    assert variant.answer is ungated_answer
    assert variant.name == base.name
    assert variant.gold_dir == base.gold_dir
    assert variant.build_graph is base.build_graph
    assert variant.build_kb is base.build_kb
    assert variant.synthetic is base.synthetic
    # Generous by design: the baseline is scored with the vertical's own
    # claim grammars, exactly like the real engine (spec 0122 decision 2).
    assert variant.claim_shapes == base.claim_shapes


def test_ungated_answer_ignores_engine_dispatch() -> None:
    """The baseline has no routing: any engine value yields the same
    retrieve-and-recite answer, claims verbatim from the records."""
    from tessera.eval.battery import GoldCase
    from tessera.retrieval import answer as plain_retrieval

    battery = business_battery()
    graph = battery.build_graph()
    kb: KnowledgeBase = battery.build_kb()
    question = "What do we know about Müller Logistik?"
    answers = [
        ungated_answer(
            GoldCase(id="x", question=question, engine=engine, kind="answer"),
            graph,
            kb,
        )
        for engine in ("compose", "route", "retrieve", "rca")
    ]
    expected = plain_retrieval(question, kb)
    for got in answers:
        assert got.claims == expected.claims
    record_texts = {record.text for record in kb.records}
    for claim in expected.claims:
        assert claim.text in record_texts  # recitation, verbatim


def test_case_outcome_marks_name_the_failed_checks() -> None:
    ok = CaseOutcome("c", "answer", "compose", True, True, True)
    assert ok.trustworthy and ok.marks() == "✓"
    bad = CaseOutcome("c", "answer", "compose", False, True, False)
    assert not bad.trustworthy and bad.marks() == "✗ F+Q"


def test_benchmark_covers_every_registered_battery(report: BenchmarkReport) -> None:
    """Nothing measured is silently missing from the artifact."""
    assert {row.battery for row in report.rows} == {b.name for b in batteries()}
    assert {row.case_set for row in report.rows} == {"gold", "synthetic"}
