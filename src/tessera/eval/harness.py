"""The eval harness: score every battery's gold + synthetic cases, one way.

Scoring is a single, vertical-neutral function over whatever batteries the
registry provides (ADR 0009): for each battery, the curated gold set (the
human-checked anchor) and the generated synthetic battery (scale) are scored
into the same three metrics —

- **Faithfulness** — fraction of emitted claims deterministically supported
  by their cited evidence (:mod:`tessera.eval.metrics`). The one hard floor:
  any battery's gold *or* synthetic faithfulness < 1.0 is a build failure
  (enforced by the CLI). Provably able to fail (ADR 0005).
- **Coverage** — fraction of each answerable case's *expected* supporting
  evidence the answer actually surfaces. Reported, not gated.
- **Quality** — fraction of cases answered correctly (answerable: the
  expected facts appear; refusal: the system refuses). Reported, not gated.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from tessera.eval.battery import Battery, GoldCase
from tessera.eval.metrics import is_supported
from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import KnowledgeBase

if TYPE_CHECKING:
    from tessera.semantic import SemanticRetriever

__all__ = ["BatteryResult", "EvalReport", "GoldCase", "load_gold_set", "run_eval"]


@dataclass(frozen=True)
class BatteryResult:
    """One battery's scores: gold and synthetic, kept separate (ADR 0007)."""

    name: str
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

    def summary(self) -> str:
        if not self.evaluated:
            return f"[{self.name}] no gold set evaluated yet (0 gold cases)."
        text = (
            f"[{self.name}] gold ({self.gold_case_count} case(s)): "
            f"faithfulness {_fmt(self.faithfulness)} (floor 1.000), "
            f"coverage {_fmt(self.coverage)}, quality {_fmt(self.quality)}."
        )
        if self.synthetic_case_count:
            text += (
                f"\n[{self.name}] synthetic ({self.synthetic_case_count} "
                f"case(s)): faithfulness {_fmt(self.synthetic_faithfulness)} "
                f"(floor 1.000), coverage {_fmt(self.synthetic_coverage)}, "
                f"quality {_fmt(self.synthetic_quality)}."
            )
        return text


@dataclass(frozen=True)
class EvalReport:
    """The outcome of an eval run: every measured vertical, scored alike."""

    batteries: tuple[BatteryResult, ...]

    @property
    def evaluated(self) -> bool:
        return any(battery.evaluated for battery in self.batteries)

    @property
    def floor_holds(self) -> bool:
        """The one hard gate: every measured faithfulness — gold and
        synthetic, every battery — is 1.0."""
        for battery in self.batteries:
            for value in (battery.faithfulness, battery.synthetic_faithfulness):
                if value is not None and value < 1.0:
                    return False
        return True

    def summary(self) -> str:
        if not self.evaluated:
            return (
                "Eval: no gold set evaluated yet — "
                "faithfulness/coverage/quality: n/a (0 gold cases)."
            )
        return "\n".join(battery.summary() for battery in self.batteries)


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def load_gold_set(gold_dir: Path) -> list[GoldCase]:
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


def _score(
    cases: list[GoldCase],
    battery: Battery,
    graph: KnowledgeGraph,
    kb: KnowledgeBase,
    nodes: dict[str, Node],
    index: SemanticRetriever | None = None,
) -> tuple[float, float, float]:
    """Faithfulness, coverage, quality over a case list (shared semantics)."""
    total_claims = supported_claims = 0
    expected_total = expected_found = 0
    correct = 0

    for case in cases:
        answer = battery.answer(case, graph, kb, index)

        # Faithfulness is scored over every emitted claim regardless of case kind
        # (spec 0110, audit B7): a refuse-kind case that wrongly ANSWERS — or a
        # partial answer that carries claims alongside its refusal — must not
        # escape the verifier. Before this, refuse-kind claims were never checked.
        for claim in answer.claims:
            total_claims += 1
            if is_supported(claim, nodes, graph, battery.claim_shapes):
                supported_claims += 1

        if case.kind == "refuse":
            if not answer.is_grounded:
                correct += 1
            continue

        # Answerable case: coverage, quality.
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


def _run_battery(battery: Battery) -> BatteryResult:
    cases = load_gold_set(battery.gold_dir)
    if not cases:
        return BatteryResult(name=battery.name, gold_case_count=0)

    graph = battery.build_graph()
    kb = battery.build_kb()
    nodes: dict[str, Node] = {node.id: node for node in graph.nodes}

    # Semantic retrieval is opt-in per battery and configured per environment:
    # built once here (None in the default offline/CI mode → lexical fallback),
    # then shared across this battery's gold and synthetic scoring (ADR 0015).
    index: SemanticRetriever | None = None
    if battery.uses_semantic:
        from tessera.semantic import build_semantic_index

        index = build_semantic_index(kb.records)

    faithfulness, coverage, quality = _score(cases, battery, graph, kb, nodes, index)
    synthetic = battery.synthetic(graph, kb)
    syn_faithfulness, syn_coverage, syn_quality = _score(
        synthetic, battery, graph, kb, nodes, index
    )

    return BatteryResult(
        name=battery.name,
        gold_case_count=len(cases),
        faithfulness=faithfulness,
        coverage=coverage,
        quality=quality,
        synthetic_case_count=len(synthetic),
        synthetic_faithfulness=syn_faithfulness,
        synthetic_coverage=syn_coverage,
        synthetic_quality=syn_quality,
    )


def run_eval(batteries: Sequence[Battery] | None = None) -> EvalReport:
    """Score every battery (defaults to the registry's measured set)."""
    if batteries is None:
        from tessera.eval.registry import batteries as registered

        batteries = registered()
    return EvalReport(batteries=tuple(_run_battery(battery) for battery in batteries))
