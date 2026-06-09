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
from tessera.grounding import Answer
from tessera.knowledge import DEMO_KB, build_demo_graph
from tessera.retrieval import answer as retrieve_answer

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
    """The outcome of an eval run. Metrics are ``None`` only when there is no gold
    set to score."""

    gold_case_count: int
    faithfulness: float | None = None
    coverage: float | None = None
    quality: float | None = None

    @property
    def evaluated(self) -> bool:
        return self.gold_case_count > 0

    def summary(self) -> str:
        if not self.evaluated:
            return (
                "Eval: no gold set evaluated yet — "
                "faithfulness/coverage/quality: n/a (0 gold cases). "
                "The gold set and metrics arrive in Unit 6 (see specs/0011)."
            )
        return (
            f"Eval over {self.gold_case_count} gold case(s): "
            f"faithfulness {_fmt(self.faithfulness)} (floor 1.000), "
            f"coverage {_fmt(self.coverage)}, quality {_fmt(self.quality)}."
        )


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


def _answer_for(case: GoldCase, graph: object) -> Answer:
    if case.engine == "compose":
        return compose(case.question, graph)  # type: ignore[arg-type]
    return retrieve_answer(case.question, DEMO_KB)


def run_eval(gold_dir: Path = GOLD_DIR) -> EvalReport:
    """Score faithfulness, coverage, and quality over the curated gold set."""
    cases = load_gold_set(gold_dir)
    if not cases:
        return EvalReport(gold_case_count=0)

    graph = build_demo_graph()
    nodes = {node.id: node for node in graph.nodes}

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
            if is_supported(claim, nodes):
                supported_claims += 1

        cited = {rec.id for claim in answer.claims for rec in claim.support}
        for support_id in case.expected_support:
            expected_total += 1
            if support_id in cited:
                expected_found += 1

        rendered = answer.render()
        if answer.is_grounded and all(fact in rendered for fact in case.expected_facts):
            correct += 1

    return EvalReport(
        gold_case_count=len(cases),
        faithfulness=(supported_claims / total_claims) if total_claims else 1.0,
        coverage=(expected_found / expected_total) if expected_total else 1.0,
        quality=correct / len(cases),
    )
