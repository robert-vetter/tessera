"""The eval harness: load the curated gold set, run the engine, score three metrics.

- **Faithfulness** — fraction of emitted claims deterministically supported by
  their cited evidence (see :mod:`tessera.eval.metrics`). A hard floor: < 1.0 is a
  build failure (enforced by the CLI). The check is provably able to fail (ADR
  0005); ``test_metrics`` injects an unfaithful claim and confirms it is caught.
- **Coverage** — fraction of each answerable case's *expected* supporting evidence
  the answer actually surfaces. Reported, not gated; expected < 1.0 (e.g. the
  Lumière document-mention miss).
- **Quality** — fraction of gold cases answered correctly (answerable: the expected
  facts appear; refusal: the system refuses). Reported, not gated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from tessera.composition import compose
from tessera.eval.metrics import is_supported
from tessera.graph import KnowledgeGraph
from tessera.grounding import Answer
from tessera.knowledge import DEMO_KB, build_demo_graph
from tessera.retrieval import answer as retrieve_answer
from tessera.routing import route

GOLD_DIR = Path(__file__).resolve().parents[3] / "eval" / "gold"


@dataclass(frozen=True)
class GoldCase:
    """One curated, human-checked evaluation case.

    ``kind`` is ``"answer"`` or ``"refuse"``; ``engine`` is ``"compose"`` or
    ``"retrieve"``. ``expected_support`` are the evidence ids a faithful answer
    should surface (coverage); ``expected_facts`` are substrings a correct answer
    must contain (quality).
    """

    id: str
    question: str
    engine: str
    kind: str
    expected_support: tuple[str, ...] = ()
    expected_facts: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvalReport:
    """The outcome of an eval run: the curated gold set (the human-checked
    anchor) and the synthetic battery (scale; ADR 0007), scored separately.
    Gold metrics are ``None`` only when there is no gold set to score."""

    gold_case_count: int
    faithfulness: float | None = None
    coverage: float | None = None
    quality: float | None = None
    synthetic_case_count: int = 0
    synthetic_faithfulness: float | None = None
    synthetic_coverage: float | None = None
    synthetic_quality: float | None = None

    @property
    def evaluated(self) -> bool:
        return self.gold_case_count > 0

    @property
    def floor_holds(self) -> bool:
        """The one hard gate: every measured faithfulness is 1.0."""
        for value in (self.faithfulness, self.synthetic_faithfulness):
            if value is not None and value < 1.0:
                return False
        return True

    def summary(self) -> str:
        if not self.evaluated:
            return (
                "Eval: no gold set evaluated yet — "
                "faithfulness/coverage/quality: n/a (0 gold cases). "
                "The gold set and metrics arrive in Unit 6 (see specs/0011)."
            )
        lines = (
            f"Eval over {self.gold_case_count} gold case(s): "
            f"faithfulness {_fmt(self.faithfulness)} (floor 1.000), "
            f"coverage {_fmt(self.coverage)}, quality {_fmt(self.quality)}."
        )
        if self.synthetic_case_count:
            lines += (
                f"\nSynthetic battery ({self.synthetic_case_count} generated "
                f"case(s)): faithfulness {_fmt(self.synthetic_faithfulness)} "
                f"(floor 1.000), coverage {_fmt(self.synthetic_coverage)}, "
                f"quality {_fmt(self.synthetic_quality)}."
            )
        return lines


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def load_gold_set(gold_dir: Path = GOLD_DIR) -> list[GoldCase]:
    """Load every gold case (one ``*.json`` per case), ordered by filename."""
    if not gold_dir.is_dir():
        return []
    cases: list[GoldCase] = []
    for path in sorted(gold_dir.glob("*.json")):
        data = json.loads(path.read_text("utf-8"))
        cases.append(
            GoldCase(
                id=str(data["id"]),
                question=str(data["question"]),
                engine=str(data["engine"]),
                kind=str(data["kind"]),
                expected_support=tuple(data.get("expected_support", ())),
                expected_facts=tuple(data.get("expected_facts", ())),
            )
        )
    return cases


def _answer_for(case: GoldCase, graph: KnowledgeGraph) -> Answer:
    if case.engine == "compose":
        return compose(case.question, graph)
    if case.engine == "route":
        return route(case.question, graph, DEMO_KB)[1]
    return retrieve_answer(case.question, DEMO_KB)


def _score(
    cases: list[GoldCase],
    graph: KnowledgeGraph,
    nodes: dict[str, object],
) -> tuple[float, float, float]:
    """Faithfulness, coverage, quality over a case list (shared semantics)."""
    total_claims = supported_claims = 0
    expected_total = expected_found = 0
    correct = 0

    for case in cases:
        answer = _answer_for(case, graph)

        if case.kind == "refuse":
            if not answer.is_grounded:
                correct += 1
            continue

        # Answerable case: faithfulness, coverage, quality.
        for claim in answer.claims:
            total_claims += 1
            if is_supported(claim, nodes, graph):  # type: ignore[arg-type]
                supported_claims += 1

        cited = {rec.id for claim in answer.claims for rec in claim.support}
        for support_id in case.expected_support:
            expected_total += 1
            if support_id in cited:
                expected_found += 1

        rendered = answer.render()
        if answer.is_grounded and all(fact in rendered for fact in case.expected_facts):
            correct += 1

    return (
        (supported_claims / total_claims) if total_claims else 1.0,
        (expected_found / expected_total) if expected_total else 1.0,
        correct / len(cases) if cases else 1.0,
    )


def run_eval(gold_dir: Path = GOLD_DIR) -> EvalReport:
    """Score the curated gold set and the generated synthetic battery."""
    cases = load_gold_set(gold_dir)
    if not cases:
        return EvalReport(gold_case_count=0)

    # Imported here to avoid a circular import (synthetic builds GoldCase).
    from tessera.eval.synthetic import generate_cases

    graph = build_demo_graph()
    nodes: dict[str, object] = {node.id: node for node in graph.nodes}

    faithfulness, coverage, quality = _score(cases, graph, nodes)
    synthetic = generate_cases(graph, DEMO_KB)
    syn_faithfulness, syn_coverage, syn_quality = _score(synthetic, graph, nodes)

    return EvalReport(
        gold_case_count=len(cases),
        faithfulness=faithfulness,
        coverage=coverage,
        quality=quality,
        synthetic_case_count=len(synthetic),
        synthetic_faithfulness=syn_faithfulness,
        synthetic_coverage=syn_coverage,
        synthetic_quality=syn_quality,
    )
