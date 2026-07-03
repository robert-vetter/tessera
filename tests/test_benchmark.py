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
from tessera.platform.config import EMBEDDINGS_NONE, load_config

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "BENCHMARK.md"

# The benchmark is pinned offline (index=None on both sides); the eval-equality
# pin additionally compares against run_eval(), which DOES honour a configured
# embeddings environment. CI is key-free so the comparison is stable there;
# skip only in a deliberately configured online environment. (Parsed by the
# platform config itself, not re-implemented here.)
_ONLINE = load_config().embeddings != EMBEDDINGS_NONE


@pytest.fixture(scope="module")
def report() -> BenchmarkReport:
    return run_benchmark()


def test_published_tables_match_fresh_run(report: BenchmarkReport) -> None:
    """Doc pin: regenerate the block and compare byte-for-byte."""
    doc = DOC_PATH.read_text("utf-8")
    # Exactly one marker pair: a second, stale pair pasted elsewhere in the
    # doc would otherwise escape the pin entirely.
    assert doc.count(DOC_BEGIN) == 1 and doc.count(DOC_END) == 1, (
        "docs/BENCHMARK.md must contain exactly one generated block"
    )
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
    assert variant.uses_semantic == base.uses_semantic


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
    """Nothing measured is silently missing: the full battery × case-set
    cross product is present (asserting the two sets independently would let
    a battery missing one of its rows slip through)."""
    assert {(row.battery, row.case_set) for row in report.rows} == {
        (battery.name, case_set)
        for battery in batteries()
        for case_set in ("gold", "synthetic")
    }


def test_prose_numbers_match_fresh_run(report: BenchmarkReport) -> None:
    """The doc pin covers only the generated block; these are the numbers the
    surrounding prose (and the README) quote. If a corpus change moves them,
    this fails until the prose is updated too — no silent drift anywhere."""
    by_key = {(row.battery, row.case_set): row for row in report.rows}
    doc = DOC_PATH.read_text("utf-8")

    # "How to read this honestly" quotes the gated side's own gold misses.
    devex = by_key[("devex", "gold")].tessera.trustworthy
    gha = by_key[("github_actions", "gold")].tessera.trustworthy
    assert f"`devex` gold shows {devex:.3f} trustworthy" in doc
    assert f"`github_actions` gold shows {gha:.3f}" in doc

    # "Limitations" states the case totals.
    total = sum(row.case_count for row in report.rows)
    gold = sum(row.case_count for row in report.rows if row.case_set == "gold")
    synthetic = total - gold
    assert f"{total} cases ({gold} gold, {synthetic} synthetic)" in doc

    # The README quotes the six gold trustworthy rates in battery order.
    readme = (REPO_ROOT / "README.md").read_text("utf-8")
    gated = " / ".join(
        f"{by_key[(name, 'gold')].tessera.trustworthy:.3f}"
        for name in ("business", "devex", "github_actions")
    )
    ungated = " / ".join(
        f"{by_key[(name, 'gold')].ungated.trustworthy:.3f}"
        for name in ("business", "devex", "github_actions")
    )
    assert f"{gated} gated vs {ungated}" in readme.replace("**", "").replace("\n", " ")
